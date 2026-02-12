"""Document structure analyzer — Chain of Responsibility + Builder.

This module contains:

* ``BaseAnalysisHandler`` — abstract handler in the chain
* ``AnalysisContext`` — shared context flowing through the chain
* 5 concrete handlers (TitlePage, Abstract, Body, Reference, Metadata)
* ``SemanticDocumentBuilder`` — fluent builder assembled by handlers
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from apa_formatter.config.models import PaperSize
from apa_formatter.domain.models.document import Section
from apa_formatter.domain.models.enums import HeadingLevel, Language
from apa_formatter.domain.models.reference import Reference
from apa_formatter.models.semantic_document import (
    DetectedConfig,
    SemanticDocument,
    TitlePageData,
)

if TYPE_CHECKING:
    from apa_formatter.importers.strategies.docx_semantic import ContentBlock


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REFERENCES_KEYWORDS = {"referencias", "references", "bibliografía", "bibliography"}
_ABSTRACT_KEYWORDS = {"abstract", "resumen"}

# Cover-page institution patterns (Spanish & English)
_INSTITUTION_RE = re.compile(
    r"\b(universidad|university|facultad|faculty|instituto|institute"
    r"|escuela|school|departamento|department|politécnico|sena)\b",
    re.IGNORECASE,
)

# Date pattern (year at end of line, or explicit date strings)
_DATE_RE = re.compile(
    r"(?:\d{1,2}\s+(?:de\s+)?\w+\s+(?:de\s+)?\d{4}"  # 12 de marzo de 2024
    r"|\w+\s+\d{1,2},?\s*\d{4}"  # March 12, 2024
    r"|\b(?:19|20)\d{2}\b)",  # standalone year 1900-2099 (word boundary)
)

# Regex to strip numbering prefixes like "1.", "2.3", "IV." from headings
_NUM_PREFIX_RE = re.compile(r"^[\d.ivxIVX]+\.?\s*")

# Metadata key patterns found on title pages (Spanish & English)
_META_KEY_RE = re.compile(
    r"\b(proyecto|project|ficha|programa|author?|autore?s?"
    r"|fecha|date|curso|course|asignatura|materia"
    r"|profesor|instructor|docente|teacher)\s*:",
    re.IGNORECASE,
)

# Bullet markers (PDF artifacts)
_BULLET_RE = re.compile(r"^[●•▪◦○\-–—]\s*")


def _heading_matches(text: str, keywords: set[str]) -> bool:
    """Check if a heading text contains any of the *keywords*.

    Strips numbering prefixes ("9.", "2.1") and checks each word.
    Matches headings like "9. REFERENCIAS Y BIBLIOGRAFÍA".
    """
    cleaned = _NUM_PREFIX_RE.sub("", text).strip().lower()
    words = set(cleaned.split())
    return bool(words & keywords)


def _count_metadata_fields(text: str) -> int:
    """Count metadata key-value fields in *text* (e.g. ``Autor: X``)."""
    return len(_META_KEY_RE.findall(text))


# Spanish stop-words for language detection
_SPANISH_WORDS = frozenset(
    "el la los las un una unos unas de del en con por para al es"
    " que se no lo le su como más pero fue ser ha han son está".split()
)

# English stop-words for language detection
_ENGLISH_WORDS = frozenset(
    "the a an of in to and is for on it that are was with as at"
    " be this from by or have not but they".split()
)


# ---------------------------------------------------------------------------
# Analysis Context
# ---------------------------------------------------------------------------


@dataclass
class AnalysisContext:
    """Shared context passed through the handler chain.

    Carries the parsed ``ContentBlock`` list and a reference to the
    ``SemanticDocumentBuilder`` that handlers populate.
    """

    blocks: list[ContentBlock]
    builder: SemanticDocumentBuilder
    source_path: str = ""

    # Internal bookkeeping — handlers can mark blocks as "consumed"
    consumed_indices: set[int] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Base Handler (Chain of Responsibility)
# ---------------------------------------------------------------------------


class BaseAnalysisHandler(ABC):
    """Abstract handler in the document analysis chain."""

    def __init__(self) -> None:
        self._next: BaseAnalysisHandler | None = None

    def set_next(self, handler: BaseAnalysisHandler) -> BaseAnalysisHandler:
        """Link the next handler and return it (allows chaining)."""
        self._next = handler
        return handler

    def handle(self, ctx: AnalysisContext) -> None:
        """Process the context, then delegate to the next handler."""
        self._process(ctx)
        if self._next:
            self._next.handle(ctx)

    @abstractmethod
    def _process(self, ctx: AnalysisContext) -> None:
        """Concrete analysis logic.  Subclasses must implement."""


# ---------------------------------------------------------------------------
# Handler 1: Title Page Detection
# ---------------------------------------------------------------------------


class TitlePageHandler(BaseAnalysisHandler):
    """Detect and extract title page elements from the first page.

    Heuristics:
      - Centred + bold text → candidate for title
      - Institution pattern ("Universidad", "Facultad") → affiliation
      - Names after title → authors
      - Date pattern at bottom → date
    """

    # Maximum blocks to consider as belonging to the title page when
    # page_index is unreliable (all blocks share the same page).
    _MAX_TITLE_PAGE_BLOCKS = 15

    def _process(self, ctx: AnalysisContext) -> None:
        # Gather first-page candidate blocks
        first_page_raw = [
            (i, b) for i, b in enumerate(ctx.blocks) if b.page_index == 0 and b.text.strip()
        ]

        if len(first_page_raw) < 2:
            return  # Not enough content for a title page

        # ── Guard against unreliable page_index ────────────────────────
        # Many DOCX files lack explicit page breaks, so *every* block
        # gets page_index=0.  When the first page contains a suspiciously
        # large number of blocks, limit it to blocks before the first
        # body heading (heading level 2+) or a hard cap.
        first_page = self._limit_title_page_scope(first_page_raw)

        # Score how "title-page-like" these blocks look
        centered_count = sum(1 for _, b in first_page if b.is_centered)
        has_institution = any(_INSTITUTION_RE.search(b.text) for _, b in first_page)

        # A heading 1 alone (e.g. "Introduction") doesn't imply a title page.
        # It must be followed by metadata-like lines (author, date, etc.)
        has_heading_1_with_meta = False
        if any(b.heading_level == 1 for _, b in first_page):
            # Count blocks that look like metadata: either short non-heading
            # lines, or lines containing key-value patterns (Autor:, Fecha:, etc.)
            meta_score = 0
            for _, b in first_page:
                if b.is_heading:
                    continue
                txt = b.text.strip()
                # Explicit key-value patterns (PDFs often merge multiple fields)
                kv_count = _count_metadata_fields(txt)
                if kv_count >= 2:
                    meta_score += kv_count
                elif kv_count == 1 and len(txt) < 120:
                    meta_score += 1
                elif len(txt) < 80:
                    meta_score += 1
            has_heading_1_with_meta = meta_score >= 2

        ratio = centered_count / len(first_page) if first_page else 0
        # Accept as title page if: ≥40% centered, or institution keyword found,
        # or heading 1 + metadata indicators.
        if ratio < 0.4 and not has_institution and not has_heading_1_with_meta:
            return

        # --- Extract components ---
        title = ""
        authors: list[str] = []
        affiliation: str | None = None
        course: str | None = None
        instructor: str | None = None
        date_text: str | None = None

        # Title: first bold-centered paragraph, or largest font
        largest_font: float = 0
        for _, blk in first_page:
            if blk.is_bold and blk.is_centered:
                fs = blk.font_size_pt or 0
                if fs >= largest_font and not _INSTITUTION_RE.search(blk.text):
                    title = blk.text
                    largest_font = fs
                    break

        if not title:
            # Fallback: first centred paragraph
            for _, blk in first_page:
                if blk.is_centered and blk.text.strip():
                    title = blk.text
                    break

        if not title:
            # Fallback: first heading 1
            for _, blk in first_page:
                if blk.heading_level == 1:
                    title = blk.text
                    break

        # Walk remaining first-page blocks in order
        title_seen = False
        for _, blk in first_page:
            txt = blk.text.strip()
            if txt == title:
                title_seen = True
                continue

            if not title_seen:
                continue

            # Check if this block contains merged metadata (common in PDFs)
            kv_count = _count_metadata_fields(txt)
            if kv_count >= 2:
                # Extract individual fields from merged metadata block
                self._extract_merged_metadata(
                    txt,
                    authors,
                    date_text,
                    lambda v: setattr(self, "_date_buf", v),  # noqa: B023
                )
                # Retrieve extracted date
                date_text = getattr(self, "_date_buf", date_text)
                if hasattr(self, "_date_buf"):
                    del self._date_buf
                continue

            # Institution
            if _INSTITUTION_RE.search(txt) and not affiliation:
                affiliation = txt
                continue

            # Date
            dm = _DATE_RE.search(txt)
            if dm and not date_text:
                date_text = dm.group(0)
                continue

            # Course / instructor heuristics
            lw = txt.lower()
            if any(kw in lw for kw in ("curso", "course", "asignatura", "materia")):
                course = txt
                continue
            if any(kw in lw for kw in ("profesor", "instructor", "docente", "teacher")):
                instructor = txt
                continue

            # Author heuristics:
            # "Autor: Name" or "Autores: Name1, Name2"
            if lw.startswith("autor"):
                # Strip "Autor:" / "Autores:" prefix
                _, _, name = txt.partition(":")
                name = name.strip()
                if name:
                    authors.append(name)
                continue

            # Remaining centred text → author names
            if blk.is_centered and len(txt) < 80 and not txt.endswith("."):
                authors.append(txt)

        if not authors:
            authors = ["Autor desconocido"]

        confidence = min(
            1.0,
            0.3
            + 0.2 * bool(title)
            + 0.2 * has_institution
            + 0.15 * bool(authors[0] != "Autor desconocido")
            + 0.15 * bool(date_text),
        )

        ctx.builder.set_title_page(
            TitlePageData(
                title=title or "Documento sin título",
                authors=authors,
                affiliation=affiliation,
                course=course,
                instructor=instructor,
                date_text=date_text,
                confidence=confidence,
            )
        )

        # Mark ONLY the title-page blocks as consumed (not the whole doc)
        for idx, _ in first_page:
            ctx.consumed_indices.add(idx)

    def _extract_merged_metadata(
        self, text: str, authors: list[str], date_text: str | None, set_date_cb
    ) -> None:
        """Extract fields from a merged metadata block (common in PDFs).

        Splits text by known keys (Autor:, Fecha:, etc.) and updates
        the *authors* list and *date_text* via callback.
        """
        # split by keys, keeping delimiters
        parts = _META_KEY_RE.split(text)
        # parts[0] is text before first key (often empty or project name)
        # then alternating: [key, value, key, value...]

        current_key = None
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check if this part is a key (e.g. "Autor:")
            if _META_KEY_RE.match(part + ":"):
                current_key = part.lower().rstrip(":")
                continue

            if current_key:
                # Value for the key
                if any(k in current_key for k in ("autor", "author")):
                    if part not in authors:
                        authors.append(part)
                elif any(k in current_key for k in ("fecha", "date")):
                    set_date_cb(part)
                # Reset key for next iteration
                current_key = None

    @staticmethod
    def _limit_title_page_scope(
        candidates: list[tuple[int, object]],
    ) -> list[tuple[int, object]]:
        """Limit title-page candidates to plausible title-page blocks.

        The boundary is:
        - the first *body heading* (heading level ≥ 2), OR
        - the second heading level 1 (which typically signals a numbered
          body section like "1. INTRODUCCIÓN").

        A hard cap prevents run-away consumption even when no heading exists.
        """
        result: list[tuple[int, object]] = []
        h1_count = 0
        for idx, blk in candidates:
            # A heading level ≥ 2 means body content starts here
            if blk.heading_level is not None and blk.heading_level >= 2:
                break
            # A *second* heading 1 signals body start (e.g. "1. INTRODUCCIÓN")
            if blk.heading_level == 1:
                h1_count += 1
                if h1_count > 1:
                    break
            result.append((idx, blk))
            if len(result) >= TitlePageHandler._MAX_TITLE_PAGE_BLOCKS:
                break
        return result if result else candidates[:1]


# ---------------------------------------------------------------------------
# Handler 2: Abstract Detection
# ---------------------------------------------------------------------------


class AbstractHandler(BaseAnalysisHandler):
    """Find the abstract/resumen section and extract its text + keywords."""

    def _process(self, ctx: AnalysisContext) -> None:
        abstract_start: int | None = None
        abstract_lines: list[str] = []
        keywords: list[str] = []

        for i, blk in enumerate(ctx.blocks):
            if i in ctx.consumed_indices:
                continue

            clean = blk.text.strip().lower()

            # Detect abstract heading
            if abstract_start is None:
                if (blk.is_heading or blk.is_bold) and _heading_matches(clean, _ABSTRACT_KEYWORDS):
                    abstract_start = i
                    ctx.consumed_indices.add(i)
                continue

            # Stop at next heading or empty (if we already have content)
            if blk.is_heading:
                break

            if not blk.text.strip():
                continue

            # Keywords line
            kw_match = re.match(
                r"(?:\*{0,2})(?:keywords?|palabras?\s*clave)(?:\*{0,2}):\s*(.+)",
                blk.text.strip(),
                re.IGNORECASE,
            )
            if kw_match:
                kw_text = kw_match.group(1).strip().rstrip(".")
                keywords = [k.strip() for k in kw_text.split(",") if k.strip()]
                ctx.consumed_indices.add(i)
                break

            abstract_lines.append(blk.text.strip())
            ctx.consumed_indices.add(i)

        if abstract_lines:
            ctx.builder.set_abstract(" ".join(abstract_lines))
        if keywords:
            ctx.builder.set_keywords(keywords)


# ---------------------------------------------------------------------------
# Handler 3: Body Section Mapping
# ---------------------------------------------------------------------------


class BodyHandler(BaseAnalysisHandler):
    """Map unconsumed paragraphs to domain ``Section`` objects.

    Stops at the references heading (handled by ``ReferenceHandler``).
    """

    _LEVEL_MAP = {
        1: HeadingLevel.LEVEL_1,
        2: HeadingLevel.LEVEL_2,
        3: HeadingLevel.LEVEL_3,
        4: HeadingLevel.LEVEL_4,
        5: HeadingLevel.LEVEL_5,
    }

    def _process(self, ctx: AnalysisContext) -> None:
        current_heading: str | None = None
        current_level: HeadingLevel = HeadingLevel.LEVEL_1
        current_content: list[str] = []

        for i, blk in enumerate(ctx.blocks):
            if i in ctx.consumed_indices:
                continue

            text = blk.text.strip()
            if not text:
                continue

            # Stop at references heading (leave for ReferenceHandler)
            if (blk.is_heading or blk.is_bold) and _heading_matches(text, _REFERENCES_KEYWORDS):
                break

            if blk.is_heading and blk.heading_level:
                ctx.consumed_indices.add(i)

                # Save previous section
                if current_heading is not None or current_content:
                    ctx.builder.add_section(
                        Section(
                            heading=current_heading,
                            level=current_level,
                            content="\n\n".join(current_content),
                        )
                    )

                current_heading = text
                current_level = self._LEVEL_MAP.get(blk.heading_level, HeadingLevel.LEVEL_1)
                current_content = []
            else:
                # Regular body text
                prefix = "- " if blk.is_list_item else ""
                current_content.append(f"{prefix}{text}")
                ctx.consumed_indices.add(i)

        # Flush last section
        if current_heading is not None or current_content:
            ctx.builder.add_section(
                Section(
                    heading=current_heading,
                    level=current_level,
                    content="\n\n".join(current_content),
                )
            )


# ---------------------------------------------------------------------------
# Handler 4: Reference Section Detection
# ---------------------------------------------------------------------------


class ReferenceHandler(BaseAnalysisHandler):
    """Isolate the references section and parse each entry.

    Everything after a "Referencias" / "References" heading is treated
    as a reference entry.  Each paragraph is sent to
    ``SmartReferenceParser`` for structured parsing.
    """

    def _process(self, ctx: AnalysisContext) -> None:
        in_refs = False

        for i, blk in enumerate(ctx.blocks):
            if i in ctx.consumed_indices:
                continue

            text = blk.text.strip()
            if not text:
                continue

            # Detect references heading
            if not in_refs:
                if (blk.is_heading or blk.is_bold) and _heading_matches(text, _REFERENCES_KEYWORDS):
                    in_refs = True
                    ctx.consumed_indices.add(i)
                continue

            # Everything after the heading is a reference entry
            # Strip bullet markers (common in PDF exports)
            clean_ref = _BULLET_RE.sub("", text).strip()
            if clean_ref:
                ctx.builder.add_raw_reference(clean_ref)
            ctx.consumed_indices.add(i)

        # Attempt structured parsing
        if ctx.builder._raw_references:
            try:
                from apa_formatter.infrastructure.importers.smart_parser import (
                    SmartReferenceParser,
                )

                parser = SmartReferenceParser()
                for raw in ctx.builder._raw_references:
                    parsed = parser.parse(raw)
                    if parsed:
                        ctx.builder.add_parsed_reference(parsed)
            except Exception:
                pass  # graceful degradation


# ---------------------------------------------------------------------------
# Handler 5: Metadata / Global Config Detection
# ---------------------------------------------------------------------------


class MetadataHandler(BaseAnalysisHandler):
    """Detect language and page size, assembling ``DetectedConfig``.

    Language detection uses stop-word frequency counting across all
    blocks.  Page size comes from the ``DocxSemanticParser`` properties.
    """

    def _process(self, ctx: AnalysisContext) -> None:
        # --- Language detection ---
        all_words: list[str] = []
        for blk in ctx.blocks:
            all_words.extend(blk.text.lower().split())

        word_set = Counter(all_words)
        es_score = sum(word_set.get(w, 0) for w in _SPANISH_WORDS)
        en_score = sum(word_set.get(w, 0) for w in _ENGLISH_WORDS)

        language = Language.ES if es_score >= en_score else Language.EN

        ctx.builder.set_config(
            DetectedConfig(
                language=language,
                has_title_page=ctx.builder._title_page is not None,
                has_abstract=ctx.builder._abstract is not None,
            )
        )


# ---------------------------------------------------------------------------
# Semantic Document Builder (fluent API)
# ---------------------------------------------------------------------------


class SemanticDocumentBuilder:
    """Fluent builder that produces a ``SemanticDocument``.

    Analysis handlers call ``set_*`` / ``add_*`` methods as they
    discover structure.  Call ``build()`` to materialise the result.
    """

    def __init__(self) -> None:
        self._title_page: TitlePageData | None = None
        self._abstract: str | None = None
        self._keywords: list[str] = []
        self._sections: list[Section] = []
        self._raw_references: list[str] = []
        self._parsed_references: list[Reference] = []
        self._config: DetectedConfig = DetectedConfig()
        self._source_path: str = ""

    # -- Setters (return self for fluent chaining) ---

    def set_title_page(self, data: TitlePageData) -> SemanticDocumentBuilder:
        self._title_page = data
        return self

    def set_abstract(self, text: str) -> SemanticDocumentBuilder:
        self._abstract = text
        return self

    def set_keywords(self, keywords: list[str]) -> SemanticDocumentBuilder:
        self._keywords = keywords
        return self

    def add_section(self, section: Section) -> SemanticDocumentBuilder:
        self._sections.append(section)
        return self

    def add_raw_reference(self, text: str) -> SemanticDocumentBuilder:
        self._raw_references.append(text)
        return self

    def add_parsed_reference(self, ref: Reference) -> SemanticDocumentBuilder:
        self._parsed_references.append(ref)
        return self

    def set_config(self, config: DetectedConfig) -> SemanticDocumentBuilder:
        self._config = config
        return self

    def set_source_path(self, path: str) -> SemanticDocumentBuilder:
        self._source_path = path
        return self

    # -- Build ---------------------------------------------------------------

    def build(self) -> SemanticDocument:
        """Materialise the accumulated state into a ``SemanticDocument``."""
        return SemanticDocument(
            title_page=self._title_page,
            abstract=self._abstract,
            keywords=self._keywords,
            body_sections=self._sections,
            references_raw=self._raw_references,
            references_parsed=self._parsed_references,
            detected_config=self._config,
            source_path=self._source_path,
        )
