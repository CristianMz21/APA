"""Export pre-flight validator — the Smart Export Guard.

Validates a ``SemanticDocument`` before export, catching critical APA
errors (orphan citations, missing title page) and quality warnings
(uncited references, long abstract) *before* the renderer runs.

The validator produces a structured ``ValidationReport`` that the
``SmartExportManager`` use-case inspects to decide whether to proceed,
warn, or block the export.

Key capabilities:

* **Citation extraction** — regex-based extraction of parenthetical
  and narrative citations from body text.
* **Fuzzy matching** — ``difflib.SequenceMatcher`` handles accent
  variations (``García`` ↔ ``Garcia``) without extra dependencies.
* **Six validation rules** covering referential integrity, APA 7
  structure, and text sanity.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import NamedTuple

from apa_formatter.models.semantic_document import SemanticDocument

# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Severity level for a validation issue."""

    ERROR = "error"  # Blocks export
    WARNING = "warning"  # Advisory — user can force export
    INFO = "info"  # Informational, never blocks


# ---------------------------------------------------------------------------
# Issue codes
# ---------------------------------------------------------------------------


class IssueCode(str, Enum):
    """Machine-readable codes for every validation rule."""

    CITE_ORPHAN = "CITE_ORPHAN"  # Citation without matching reference
    REF_UNCITED = "REF_UNCITED"  # Reference never cited in text
    NO_TITLE_PAGE = "NO_TITLE_PAGE"  # Missing title page
    ABSTRACT_TOO_LONG = "ABSTRACT_TOO_LONG"  # Abstract > 250 words
    EMPTY_PARAGRAPHS = "EMPTY_PARAGRAPHS"  # Consecutive empty paragraphs
    NO_REFERENCES = "NO_REFERENCES"  # Body has citations but no refs section


# ---------------------------------------------------------------------------
# ValidationIssue & ValidationReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding."""

    severity: Severity
    code: IssueCode
    message: str
    location: str | None = None


@dataclass
class ValidationReport:
    """Aggregated result of all pre-flight checks.

    Attributes:
        issues: All findings from the validation pass.
        is_blocking: ``True`` if at least one ERROR-severity issue exists.
        timestamp: ISO-8601 timestamp of when the validation ran.
    """

    issues: list[ValidationIssue] = field(default_factory=list)
    timestamp: str = ""

    @property
    def is_blocking(self) -> bool:
        """True if any issue has ERROR severity."""
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0


# ---------------------------------------------------------------------------
# Internal: Citation extraction
# ---------------------------------------------------------------------------

# Parenthetical citation: (Author, 2020) or (Author & Co, 2020) or
# (Author et al., 2020) or (García, 2020a)
_PARENTHETICAL_RE = re.compile(
    r"\("
    r"([A-ZÁ-Úa-záéíóúñü][A-ZÁ-Úa-záéíóúñü\w\-'\.]+"  # first author
    r"(?:\s+(?:et\s+al\.|[&y]\s+[A-ZÁ-Úa-záéíóúñü][A-ZÁ-Úa-záéíóúñü\w\-'\.]+))*"  # optional 2nd / et al.
    r"),\s*"
    r"(\d{4})"  # year
    r"([a-z])?"  # optional year suffix
    r"\)"
)

# Narrative citation: Author (2020) or Author et al. (2020)
_NARRATIVE_RE = re.compile(
    r"([A-ZÁ-Ú][a-záéíóúñü\w\-'\.]+"  # first author
    r"(?:\s+(?:et\s+al\.|[&y]\s+[A-ZÁ-Ú][a-záéíóúñü\w\-'\.]+))*)"
    r"\s+\((\d{4})([a-z])?\)"
)


class _CitationKey(NamedTuple):
    """Normalized citation for matching: (author_surname, year)."""

    surname: str
    year: int


def _normalize(text: str) -> str:
    """Strip accents and lower-case for fuzzy comparison."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _extract_citations(text: str) -> list[_CitationKey]:
    """Extract all citation keys from body text."""
    keys: list[_CitationKey] = []

    for m in _PARENTHETICAL_RE.finditer(text):
        surname = m.group(1).split()[0]  # first token = primary surname
        year = int(m.group(2))
        keys.append(_CitationKey(_normalize(surname), year))

    for m in _NARRATIVE_RE.finditer(text):
        surname = m.group(1).split()[0]
        year = int(m.group(2))
        keys.append(_CitationKey(_normalize(surname), year))

    return keys


def _build_ref_keys(doc: SemanticDocument) -> list[tuple[str, int, str]]:
    """Build (normalized_surname, year, original_label) for each reference."""
    keys: list[tuple[str, int, str]] = []
    for ref in doc.references_parsed:
        if not ref.authors:
            continue
        first_author = ref.authors[0]
        surname = getattr(first_author, "last_name", None) or getattr(
            first_author, "name", str(first_author)
        )
        year = ref.year or 0
        label = f"{surname} ({year})" if year else surname
        keys.append((_normalize(surname), year, label))

    # Also try to extract from raw references if parsed is empty
    if not keys and doc.references_raw:
        raw_re = re.compile(r"^([A-ZÁ-Úa-záéíóúñü\w\-'\.]+).*?\((\d{4})\)")
        for raw in doc.references_raw:
            m = raw_re.match(raw.strip())
            if m:
                keys.append((_normalize(m.group(1)), int(m.group(2)), raw[:40]))
    return keys


def _fuzzy_match(cite_surname: str, ref_surname: str, threshold: float = 0.80) -> bool:
    """Fuzzy surname match using SequenceMatcher."""
    if cite_surname == ref_surname:
        return True
    return SequenceMatcher(None, cite_surname, ref_surname).ratio() >= threshold


# ---------------------------------------------------------------------------
# ExportValidator
# ---------------------------------------------------------------------------


class ExportValidator:
    """Pre-flight validation engine for ``SemanticDocument`` export.

    Runs all registered rules and returns a ``ValidationReport``.
    Designed to be fast (no I/O) so it won't freeze the GUI.
    """

    # Maximum abstract word count per APA 7 (§2.9)
    APA_ABSTRACT_MAX_WORDS: int = 250

    # Fuzzy matching threshold for surname comparison
    FUZZY_THRESHOLD: float = 0.80

    def validate(self, doc: SemanticDocument) -> ValidationReport:
        """Run all pre-flight checks and return the report."""
        issues: list[ValidationIssue] = []

        issues.extend(self._check_referential_integrity(doc))
        issues.extend(self._check_title_page(doc))
        issues.extend(self._check_abstract_length(doc))
        issues.extend(self._check_empty_paragraphs(doc))

        return ValidationReport(
            issues=issues,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # -- Rule implementations ------------------------------------------------

    def _check_referential_integrity(self, doc: SemanticDocument) -> list[ValidationIssue]:
        """Check citation↔reference matching."""
        issues: list[ValidationIssue] = []

        # Gather all body text
        body_text = self._collect_body_text(doc)
        citations = _extract_citations(body_text)
        ref_keys = _build_ref_keys(doc)

        # If we have citations but absolutely no references → ERROR
        if citations and not ref_keys and not doc.references_raw:
            issues.append(
                ValidationIssue(
                    severity=Severity.ERROR,
                    code=IssueCode.NO_REFERENCES,
                    message=(
                        f"Se encontraron {len(citations)} citas en el texto "
                        "pero no hay sección de referencias."
                    ),
                )
            )
            return issues  # No point checking per-citation

        # Check each citation has a matching reference
        matched_ref_indices: set[int] = set()
        seen_cites: set[_CitationKey] = set()

        for cite in citations:
            if cite in seen_cites:
                continue
            seen_cites.add(cite)

            found = False
            for idx, (ref_surname, ref_year, _label) in enumerate(ref_keys):
                if cite.year == ref_year and _fuzzy_match(
                    cite.surname, ref_surname, self.FUZZY_THRESHOLD
                ):
                    found = True
                    matched_ref_indices.add(idx)
                    break

            if not found:
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        code=IssueCode.CITE_ORPHAN,
                        message=(
                            f"La cita ({cite.surname.title()}, {cite.year}) "
                            "no tiene referencia correspondiente en la bibliografía."
                        ),
                    )
                )

        # Check uncited references
        for idx, (_surname, _year, label) in enumerate(ref_keys):
            if idx not in matched_ref_indices:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        code=IssueCode.REF_UNCITED,
                        message=(
                            f"La referencia «{label}» aparece en la bibliografía "
                            "pero nunca se cita en el texto."
                        ),
                    )
                )

        return issues

    def _check_title_page(self, doc: SemanticDocument) -> list[ValidationIssue]:
        """Check that a title page exists."""
        if doc.title_page is None:
            return [
                ValidationIssue(
                    severity=Severity.ERROR,
                    code=IssueCode.NO_TITLE_PAGE,
                    message="El documento no tiene portada (título, autor, institución).",
                )
            ]

        issues: list[ValidationIssue] = []
        tp = doc.title_page

        if not tp.title or tp.title == "Documento sin título":
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code=IssueCode.NO_TITLE_PAGE,
                    message="La portada no tiene un título definido.",
                    location="Portada",
                )
            )

        if not tp.authors or tp.authors == ["Autor desconocido"]:
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code=IssueCode.NO_TITLE_PAGE,
                    message="La portada no tiene autores definidos.",
                    location="Portada",
                )
            )

        return issues

    def _check_abstract_length(self, doc: SemanticDocument) -> list[ValidationIssue]:
        """Warn if abstract exceeds APA 7 maximum."""
        if not doc.abstract:
            return []

        word_count = len(doc.abstract.split())
        if word_count > self.APA_ABSTRACT_MAX_WORDS:
            return [
                ValidationIssue(
                    severity=Severity.WARNING,
                    code=IssueCode.ABSTRACT_TOO_LONG,
                    message=(
                        f"El resumen tiene {word_count} palabras "
                        f"(máx. recomendado: {self.APA_ABSTRACT_MAX_WORDS})."
                    ),
                    location="Resumen/Abstract",
                )
            ]
        return []

    def _check_empty_paragraphs(self, doc: SemanticDocument) -> list[ValidationIssue]:
        """Detect sections with empty content or multiple blank lines."""
        issues: list[ValidationIssue] = []
        empty_count = 0

        for section in doc.body_sections:
            self._scan_section_empties(section, issues, empty_count)

        return issues

    def _scan_section_empties(
        self,
        section,
        issues: list[ValidationIssue],
        empty_count: int,
    ) -> None:
        """Recursively scan sections for empty paragraphs."""
        content = section.content.strip() if section.content else ""

        if not content:
            heading = section.heading or "Sin título"
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code=IssueCode.EMPTY_PARAGRAPHS,
                    message=f"La sección «{heading}» no tiene contenido.",
                    location=f"Sección: {heading}",
                )
            )

        # Check for multiple consecutive blank lines within content
        if content and "\n\n\n" in content:
            heading = section.heading or "Sin título"
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code=IssueCode.EMPTY_PARAGRAPHS,
                    message=(f"Se detectaron saltos de línea múltiples en la sección «{heading}»."),
                    location=f"Sección: {heading}",
                )
            )

        for sub in section.subsections:
            self._scan_section_empties(sub, issues, empty_count)

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _collect_body_text(doc: SemanticDocument) -> str:
        """Concatenate all body section text for citation scanning."""
        parts: list[str] = []

        def _gather(sections):
            for s in sections:
                if s.content:
                    parts.append(s.content)
                if s.subsections:
                    _gather(s.subsections)

        _gather(doc.body_sections)
        return " ".join(parts)
