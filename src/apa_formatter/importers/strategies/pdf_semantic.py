"""Smart PDF semantic parser strategy.

Reads a PDF file using ``pdfplumber`` and produces a list of
``ContentBlock`` objects — the same intermediate representation used by
``DocxSemanticParser`` — preserving paragraph-level formatting metadata
(bold, font, page index) for downstream analysis handlers.

Key capabilities:

* **Header / page-number filtering** — words in the top ~8 % of each
  page that match running-head or bare-number patterns are stripped from
  the body text but stored as page metadata.
* **Bold detection** — the PDF font name (e.g. ``TimesNewRomanPS-BoldMT``)
  is inspected; if it contains ``Bold`` the corresponding ``ContentBlock``
  is flagged ``is_bold=True``.
* **Paragraph stitching** — lines that end well short of the right margin
  signal a paragraph break; otherwise they are joined.
* **Cross-page merge** — if a page ends without terminal punctuation and
  the next page begins with a lowercase letter or continuation token, the
  two fragments are fused into a single paragraph.
* **Section heading detection** — numbered headings (``1.1 Propósito``)
  and ALL-CAPS titles (``ABSTRACT``, ``REFERENCIAS``) are promoted to
  ``ContentBlock.heading_level``.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber

from apa_formatter.importers.strategies.docx_semantic import ContentBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Words in the top fraction of the page are candidate headers
_HEADER_ZONE_FRACTION = 0.08

# Footer zone (bottom fraction) — page numbers at the bottom
_FOOTER_ZONE_FRACTION = 0.06

# If a line ends before this fraction of the page width → paragraph break
_RIGHT_MARGIN_THRESHOLD = 0.75

# Y-coordinate tolerance for grouping words into lines (pt)
_LINE_Y_TOLERANCE = 3.0

# Regex: bare page number (1–4 digits, optionally with decorations)
_PAGE_NUM_RE = re.compile(r"^[\-–—]?\s*\d{1,4}\s*[\-–—]?$")

# Regex: numbered heading  e.g. "1. Introducción", "2.3.1 Método"
_NUMBERED_HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})[\.\s]+\S")

# Regex: ALL-CAPS title (≥3 consecutive uppercase letters, short text)
_ALL_CAPS_RE = re.compile(r"^[A-ZÁÉÍÓÚÑÜ\s\d]{3,}$")

# Terminal punctuation that signals end-of-paragraph
_TERMINAL_PUNCT = frozenset(".!?;:)")

# Running-head: short text that repeats across ≥ 50 % of pages
_MIN_RUNNING_HEAD_RATIO = 0.50


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------


@dataclass
class _Word:
    """A single word extracted from pdfplumber with spatial + font data."""

    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    fontname: str = ""
    size: float = 0.0

    @property
    def is_bold(self) -> bool:
        return "Bold" in self.fontname or "bold" in self.fontname


@dataclass
class _Line:
    """A reconstructed line of text (one visual row on the page)."""

    words: list[_Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def is_bold(self) -> bool:
        """True if ALL words in the line are bold."""
        return bool(self.words) and all(w.is_bold for w in self.words)

    @property
    def has_bold(self) -> bool:
        """True if ANY word in the line is bold."""
        return any(w.is_bold for w in self.words)

    @property
    def dominant_font(self) -> str:
        if not self.words:
            return ""
        fonts = Counter(w.fontname for w in self.words)
        return fonts.most_common(1)[0][0]

    @property
    def dominant_size(self) -> float:
        if not self.words:
            return 0.0
        sizes = Counter(round(w.size, 1) for w in self.words)
        return sizes.most_common(1)[0][0]

    @property
    def right_edge(self) -> float:
        return max(w.x1 for w in self.words) if self.words else 0.0

    @property
    def left_edge(self) -> float:
        return min(w.x0 for w in self.words) if self.words else 0.0


@dataclass
class _Paragraph:
    """Accumulated paragraph from one or more lines."""

    lines: list[_Line] = field(default_factory=list)
    page_index: int = 0

    @property
    def text(self) -> str:
        return " ".join(ln.text for ln in self.lines)

    @property
    def is_bold(self) -> bool:
        return bool(self.lines) and all(ln.is_bold for ln in self.lines)

    @property
    def has_bold_fragments(self) -> bool:
        return any(ln.has_bold for ln in self.lines)

    @property
    def dominant_font(self) -> str:
        if not self.lines:
            return ""
        fonts = Counter(ln.dominant_font for ln in self.lines)
        return fonts.most_common(1)[0][0]

    @property
    def dominant_size(self) -> float:
        if not self.lines:
            return 0.0
        sizes = [ln.dominant_size for ln in self.lines if ln.dominant_size]
        return statistics.median(sizes) if sizes else 0.0

    @property
    def raw_runs(self) -> list[dict[str, object]]:
        """Build run-level data similar to DOCX raw_runs."""
        runs: list[dict[str, object]] = []
        for ln in self.lines:
            for w in ln.words:
                runs.append(
                    {
                        "text": w.text,
                        "bold": w.is_bold,
                        "italic": False,
                        "font_name": w.fontname,
                        "font_size": round(w.size, 1),
                    }
                )
        return runs


# ---------------------------------------------------------------------------
# SmartPdfImporter
# ---------------------------------------------------------------------------


class SmartPdfImporter:
    """Parses a PDF file into a list of ``ContentBlock`` objects.

    This is a *Strategy* — it produces the same ``ContentBlock`` list as
    ``DocxSemanticParser``, allowing the downstream handler chain
    (``TitlePageHandler`` → ``AbstractHandler`` → ``BodyHandler`` →
    ``ReferenceHandler`` → ``MetadataHandler``) to remain unchanged.
    """

    def __init__(self) -> None:
        self._all_fonts: set[str] = set()
        self._all_sizes: list[float] = []
        self._page_dims: dict[str, float] | None = None

    # ── Public API ─────────────────────────────────────────────────────

    def parse(self, path: Path) -> list[ContentBlock]:
        """Read *path* and return enriched content blocks.

        Raises ``ValueError`` if the file cannot be opened.
        """
        if not path.exists():
            raise ValueError(f"Archivo no encontrado: {path}")

        try:
            pdf = pdfplumber.open(str(path))
        except Exception as exc:
            raise ValueError(f"Error al abrir el PDF: {exc}") from exc

        try:
            return self._process_pdf(pdf)
        finally:
            pdf.close()

    # ── Core pipeline ──────────────────────────────────────────────────

    def _process_pdf(self, pdf: pdfplumber.PDF) -> list[ContentBlock]:
        pages = pdf.pages
        if not pages:
            return []

        # Store page dimensions from first page
        first = pages[0]
        self._page_dims = {
            "width_cm": (first.width or 612) * 0.03528,
            "height_cm": (first.height or 792) * 0.03528,
        }

        # Phase 1: Extract words per page + detect running heads
        all_page_words: list[list[_Word]] = []
        header_candidates: list[str] = []

        for page in pages:
            words = self._extract_page_words(page)
            all_page_words.append(words)

            # Collect header-zone texts for running-head detection
            page_h = float(page.height or 792)
            cutoff = page_h * _HEADER_ZONE_FRACTION
            for w in words:
                if w.top < cutoff:
                    header_candidates.append(w.text.strip().lower())

        # Identify running heads (text repeated in header zone of ≥ 50 % pages)
        running_heads = self._detect_running_heads(header_candidates, len(pages))

        # Phase 2: Filter headers, reconstruct lines and paragraphs per page
        all_page_paragraphs: list[list[_Paragraph]] = []

        for page_idx, (page, words) in enumerate(zip(pages, all_page_words)):
            page_h = float(page.height or 792)
            page_w = float(page.width or 612)

            # Filter out header/footer noise
            body_words = [
                w
                for w in words
                if not self._is_header_word(w, page_h, running_heads)
                and not self._is_footer_word(w, page_h)
            ]

            if not body_words:
                all_page_paragraphs.append([])
                continue

            # Reconstruct lines from word positions
            lines = self._reconstruct_lines(body_words)

            # Stitch lines into paragraphs
            paragraphs = self._stitch_paragraphs(lines, page_w, page_idx)
            all_page_paragraphs.append(paragraphs)

        # Phase 3: Cross-page paragraph merging
        flat_paragraphs = self._cross_page_merge(all_page_paragraphs)

        # Phase 4: Detect body font size (for heading heuristics)
        body_size = self._detect_body_font_size(flat_paragraphs)

        # Phase 5: Convert to ContentBlock list
        blocks: list[ContentBlock] = []
        for para in flat_paragraphs:
            text = para.text.strip()
            if not text:
                continue

            heading_level = self._detect_heading(text, para, body_size)

            block = ContentBlock(
                text=text,
                style_name="heading" if heading_level else "normal",
                alignment=None,
                is_bold=para.is_bold,
                is_italic=False,
                font_name=para.dominant_font or None,
                font_size_pt=para.dominant_size or None,
                page_index=para.page_index,
                heading_level=heading_level,
                is_list_item=False,
                has_page_break_before=False,
                raw_runs=para.raw_runs,
            )
            blocks.append(block)

            # Track fonts
            if para.dominant_font:
                self._all_fonts.add(para.dominant_font)
            if para.dominant_size:
                self._all_sizes.append(para.dominant_size)

        return blocks

    # ── Word extraction ────────────────────────────────────────────────

    def _extract_page_words(self, page: Any) -> list[_Word]:
        """Extract words with font metadata from a pdfplumber page."""
        try:
            raw_words = page.extract_words(
                extra_attrs=["fontname", "size"],
                keep_blank_chars=False,
            )
        except Exception:
            return []

        words: list[_Word] = []
        for w in raw_words:
            text = (w.get("text") or "").strip()
            if not text:
                continue
            words.append(
                _Word(
                    text=text,
                    x0=float(w.get("x0", 0)),
                    x1=float(w.get("x1", 0)),
                    top=float(w.get("top", 0)),
                    bottom=float(w.get("bottom", 0)),
                    fontname=str(w.get("fontname", "")),
                    size=float(w.get("size", 0)),
                )
            )
        return words

    # ── Header / footer filtering ──────────────────────────────────────

    @staticmethod
    def _is_header_word(word: _Word, page_height: float, running_heads: set[str]) -> bool:
        """True if *word* is a running head or page number in the header zone."""
        cutoff = page_height * _HEADER_ZONE_FRACTION
        if word.top >= cutoff:
            return False

        text = word.text.strip()

        # Bare page number
        if _PAGE_NUM_RE.match(text):
            return True

        # Known running head
        if text.lower() in running_heads:
            return True

        return False

    @staticmethod
    def _is_footer_word(word: _Word, page_height: float) -> bool:
        """True if *word* is a page number in the footer zone."""
        cutoff = page_height * (1 - _FOOTER_ZONE_FRACTION)
        if word.top < cutoff:
            return False

        text = word.text.strip()
        return bool(_PAGE_NUM_RE.match(text))

    @staticmethod
    def _detect_running_heads(header_texts: list[str], num_pages: int) -> set[str]:
        """Identify texts that repeat in ≥ 50 % of pages' header zones."""
        if num_pages < 2:
            return set()

        counter = Counter(header_texts)
        threshold = max(2, int(num_pages * _MIN_RUNNING_HEAD_RATIO))
        return {
            text
            for text, count in counter.items()
            if count >= threshold and not _PAGE_NUM_RE.match(text)
        }

    # ── Line reconstruction ────────────────────────────────────────────

    @staticmethod
    def _reconstruct_lines(words: list[_Word]) -> list[_Line]:
        """Group words into visual lines by y-coordinate proximity."""
        if not words:
            return []

        # Sort by vertical position first, then horizontal
        sorted_words = sorted(words, key=lambda w: (w.top, w.x0))

        lines: list[_Line] = []
        current_line = _Line(words=[sorted_words[0]])

        for word in sorted_words[1:]:
            # Same line if y-coordinates are within tolerance
            prev_top = current_line.words[-1].top
            if abs(word.top - prev_top) <= _LINE_Y_TOLERANCE:
                current_line.words.append(word)
            else:
                # Sort words in the line left-to-right before finalizing
                current_line.words.sort(key=lambda w: w.x0)
                lines.append(current_line)
                current_line = _Line(words=[word])

        # Don't forget the last line
        current_line.words.sort(key=lambda w: w.x0)
        lines.append(current_line)

        return lines

    # ── Paragraph stitching ────────────────────────────────────────────

    @staticmethod
    def _stitch_paragraphs(
        lines: list[_Line], page_width: float, page_index: int
    ) -> list[_Paragraph]:
        """Join consecutive lines into paragraphs using margin + punctuation heuristics."""
        if not lines:
            return []

        right_limit = page_width * _RIGHT_MARGIN_THRESHOLD
        paragraphs: list[_Paragraph] = []
        current = _Paragraph(lines=[lines[0]], page_index=page_index)

        for line in lines[1:]:
            prev_line = current.lines[-1]
            prev_text = prev_line.text.rstrip()

            # Heuristics for paragraph break:
            is_short_line = prev_line.right_edge < right_limit
            ends_with_punct = bool(prev_text) and prev_text[-1] in _TERMINAL_PUNCT

            # Significant indent change → new paragraph
            indent_diff = abs(line.left_edge - prev_line.left_edge)
            has_indent_jump = indent_diff > 20  # ~0.7cm indent change

            # Large vertical gap → new paragraph
            gap = (
                line.words[0].top - prev_line.words[-1].bottom
                if line.words and prev_line.words
                else 0
            )
            large_gap = gap > (
                prev_line.words[0].size * 1.5 if prev_line.words and prev_line.words[0].size else 15
            )

            # Font size change → likely heading / new section
            size_change = abs(line.dominant_size - prev_line.dominant_size) > 1.5

            # Boldness change can signal new paragraph
            bold_change = line.is_bold != prev_line.is_bold

            if (
                (is_short_line and ends_with_punct)
                or has_indent_jump
                or large_gap
                or size_change
                or (bold_change and (is_short_line or ends_with_punct))
            ):
                paragraphs.append(current)
                current = _Paragraph(lines=[line], page_index=page_index)
            else:
                current.lines.append(line)

        paragraphs.append(current)
        return paragraphs

    # ── Cross-page merge ───────────────────────────────────────────────

    @staticmethod
    def _cross_page_merge(
        all_page_paragraphs: list[list[_Paragraph]],
    ) -> list[_Paragraph]:
        """Merge paragraphs that are split across page boundaries.

        If page N's last paragraph lacks terminal punctuation AND page N+1's
        first paragraph starts with a lowercase letter → merge them.
        """
        flat: list[_Paragraph] = []

        for page_paras in all_page_paragraphs:
            if not page_paras:
                continue

            if flat:
                prev = flat[-1]
                first_new = page_paras[0]

                prev_text = prev.text.rstrip()
                new_text = first_new.text.lstrip()

                # Merge condition: previous doesn't end with terminal punct
                # AND next starts with lowercase or continuation
                should_merge = (
                    prev_text
                    and new_text
                    and prev_text[-1] not in _TERMINAL_PUNCT
                    and (new_text[0].islower() or new_text[0] in ",(;–—")
                )

                if should_merge:
                    # Extend previous paragraph with new lines
                    prev.lines.extend(first_new.lines)
                    flat.extend(page_paras[1:])
                else:
                    flat.extend(page_paras)
            else:
                flat.extend(page_paras)

        return flat

    # ── Heading detection ──────────────────────────────────────────────

    @staticmethod
    def _detect_heading(text: str, para: _Paragraph, body_size: float) -> int | None:
        """Detect heading level from text patterns and formatting."""
        stripped = text.strip()
        if not stripped or len(stripped) > 200:
            return None

        # 1) Numbered heading: "1. Introduction", "2.3 Method"
        m = _NUMBERED_HEADING_RE.match(stripped)
        if m:
            num_part = m.group(1)
            depth = num_part.count(".") + 1
            return min(depth, 5)

        # 2) ALL-CAPS title (short, typically ≤ 60 chars)
        if len(stripped) <= 60 and _ALL_CAPS_RE.match(stripped) and not stripped.isdigit():
            return 1

        # 3) Bold + short + larger font → heading
        if (
            para.is_bold
            and len(stripped) < 100
            and body_size > 0
            and para.dominant_size >= body_size + 1.0
        ):
            return 1

        # 4) Bold + short text (same size) → level 2
        if para.is_bold and len(stripped) < 100:
            return 2

        return None

    @staticmethod
    def _detect_body_font_size(paragraphs: list[_Paragraph]) -> float:
        """Find the most common font size (assumed to be body text)."""
        sizes: list[float] = []
        for p in paragraphs:
            s = p.dominant_size
            if s > 0:
                sizes.append(round(s, 1))

        if not sizes:
            return 12.0

        counter = Counter(sizes)
        return counter.most_common(1)[0][0]

    # ── Metadata properties ────────────────────────────────────────────

    @property
    def page_dimensions(self) -> dict[str, float] | None:
        """Page width/height in cm from the first PDF page."""
        return self._page_dims

    @property
    def detected_fonts(self) -> list[str]:
        """All font names found across document words."""
        return sorted(self._all_fonts) if self._all_fonts else []

    @property
    def dominant_line_spacing(self) -> float | None:
        """PDF doesn't embed line-spacing metadata; return None."""
        return None
