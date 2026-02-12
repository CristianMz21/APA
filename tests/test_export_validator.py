"""Tests for the Smart Export Guard system.

Covers:
1. Citation regex extraction (parenthetical + narrative)
2. Fuzzy surname matching (accent variations)
3. All 6 validation rules (CITE_ORPHAN, REF_UNCITED, NO_TITLE_PAGE,
   ABSTRACT_TOO_LONG, EMPTY_PARAGRAPHS, NO_REFERENCES)
4. ValidationReport properties
5. SmartExportManager orchestration (blocking / warning / clean flows)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apa_formatter.domain.models.document import APADocument, Section
from apa_formatter.domain.models.enums import HeadingLevel
from apa_formatter.domain.models.reference import Author, Reference
from apa_formatter.domain.models.enums import ReferenceType
from apa_formatter.models.semantic_document import (
    SemanticDocument,
    TitlePageData,
)
from apa_formatter.validators.export_validator import (
    ExportValidator,
    IssueCode,
    Severity,
    ValidationIssue,
    ValidationReport,
    _CitationKey,
    _extract_citations,
    _fuzzy_match,
    _normalize,
)
from apa_formatter.application.use_cases.smart_export import (
    ExportResult,
    SmartExportManager,
)


# ===================================================================
# Fixtures
# ===================================================================


def _make_doc(
    body_text: str = "",
    refs: list[Reference] | None = None,
    title_page: TitlePageData | None = None,
    abstract: str | None = None,
    sections: list[Section] | None = None,
) -> SemanticDocument:
    """Build a SemanticDocument for testing."""
    if sections is None and body_text:
        sections = [Section(heading="Body", level=HeadingLevel.LEVEL_1, content=body_text)]
    return SemanticDocument(
        title_page=title_page or TitlePageData(title="Test", authors=["Author"]),
        abstract=abstract,
        body_sections=sections or [],
        references_parsed=refs or [],
    )


def _make_ref(surname: str, year: int) -> Reference:
    """Build a minimal Reference with one author."""
    return Reference(
        ref_type=ReferenceType.JOURNAL_ARTICLE,
        authors=[Author(last_name=surname, first_name="A.")],
        year=year,
        title="Some Article",
    )


# ===================================================================
# 1. Citation Regex Extraction
# ===================================================================


class TestCitationExtraction:
    def test_parenthetical_basic(self):
        text = "According to research (Smith, 2020), this is true."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0] == _CitationKey("smith", 2020)

    def test_parenthetical_with_accent(self):
        text = "Se encontró evidencia (García, 2019) en el estudio."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0].surname == "garcia"
        assert keys[0].year == 2019

    def test_parenthetical_et_al(self):
        text = "Prior work (Johnson et al., 2021) supports this."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0] == _CitationKey("johnson", 2021)

    def test_parenthetical_two_authors(self):
        text = "Based on (Smith & Jones, 2018) we conclude."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0].surname == "smith"

    def test_narrative_basic(self):
        text = "Smith (2020) argued that this is important."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0] == _CitationKey("smith", 2020)

    def test_narrative_et_al(self):
        text = "García et al. (2021) demonstrated the effect."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0].surname == "garcia"

    def test_multiple_citations(self):
        text = (
            "Smith (2020) and García (2019) both found support. "
            "Additionally, (Johnson et al., 2021) confirmed this."
        )
        keys = _extract_citations(text)
        assert len(keys) == 3

    def test_no_citations(self):
        text = "This is a plain text without any citations."
        keys = _extract_citations(text)
        assert len(keys) == 0

    def test_year_suffix(self):
        text = "As noted (Smith, 2020a) and (Smith, 2020b)."
        keys = _extract_citations(text)
        assert len(keys) == 2

    def test_spanish_y_connector(self):
        text = "Según (Rodríguez y Pérez, 2022), el resultado es claro."
        keys = _extract_citations(text)
        assert len(keys) == 1
        assert keys[0].surname == "rodriguez"


# ===================================================================
# 2. Fuzzy Matching
# ===================================================================


class TestFuzzyMatching:
    def test_exact_match(self):
        assert _fuzzy_match("smith", "smith") is True

    def test_accent_variation(self):
        assert _fuzzy_match("garcia", "garcia") is True
        # Both are normalized — test raw normalization
        assert _fuzzy_match(_normalize("García"), _normalize("Garcia")) is True

    def test_completely_different(self):
        assert _fuzzy_match("smith", "johnson") is False

    def test_minor_variation(self):
        assert _fuzzy_match("rodriguez", "rodríguez".lower()) is True

    def test_normalize_strips_accents(self):
        assert _normalize("García") == "garcia"
        assert _normalize("Pérez") == "perez"
        assert _normalize("Müller") == "muller"
        assert _normalize("Señorita") == "senorita"


# ===================================================================
# 3. Validation Rules
# ===================================================================


class TestCiteOrphan:
    """CITE_ORPHAN: citation without matching reference."""

    def test_orphan_citation_produces_error(self):
        doc = _make_doc(
            body_text="As shown by (Smith, 2020), this matters.",
            refs=[],
        )
        report = ExportValidator().validate(doc)
        orphans = [i for i in report.issues if i.code == IssueCode.CITE_ORPHAN]
        # With no refs at all but citations present → NO_REFERENCES fires first
        assert report.is_blocking

    def test_orphan_with_some_refs(self):
        doc = _make_doc(
            body_text="According to (Smith, 2020) and (Jones, 2019).",
            refs=[_make_ref("Smith", 2020)],
        )
        report = ExportValidator().validate(doc)
        orphans = [i for i in report.issues if i.code == IssueCode.CITE_ORPHAN]
        assert len(orphans) == 1
        assert "Jones" in orphans[0].message or "jones" in orphans[0].message.lower()

    def test_matched_citations_no_error(self):
        doc = _make_doc(
            body_text="Smith (2020) confirmed this.",
            refs=[_make_ref("Smith", 2020)],
        )
        report = ExportValidator().validate(doc)
        orphans = [i for i in report.issues if i.code == IssueCode.CITE_ORPHAN]
        assert len(orphans) == 0

    def test_fuzzy_accent_match_no_error(self):
        """García in text should match Garcia in references."""
        doc = _make_doc(
            body_text="Según (García, 2019) el resultado es claro.",
            refs=[_make_ref("Garcia", 2019)],
        )
        report = ExportValidator().validate(doc)
        orphans = [i for i in report.issues if i.code == IssueCode.CITE_ORPHAN]
        assert len(orphans) == 0


class TestRefUncited:
    """REF_UNCITED: reference in bibliography never cited."""

    def test_uncited_reference_produces_warning(self):
        doc = _make_doc(
            body_text="Smith (2020) proved this.",
            refs=[_make_ref("Smith", 2020), _make_ref("Jones", 2018)],
        )
        report = ExportValidator().validate(doc)
        uncited = [i for i in report.issues if i.code == IssueCode.REF_UNCITED]
        assert len(uncited) == 1
        assert uncited[0].severity == Severity.WARNING
        assert "Jones" in uncited[0].message

    def test_all_refs_cited_no_warning(self):
        doc = _make_doc(
            body_text="Smith (2020) and Jones (2018) agree.",
            refs=[_make_ref("Smith", 2020), _make_ref("Jones", 2018)],
        )
        report = ExportValidator().validate(doc)
        uncited = [i for i in report.issues if i.code == IssueCode.REF_UNCITED]
        assert len(uncited) == 0


class TestNoTitlePage:
    """NO_TITLE_PAGE: missing title page data."""

    def test_missing_title_page_is_error(self):
        doc = _make_doc(body_text="Content.")
        doc.title_page = None
        report = ExportValidator().validate(doc)
        tp_issues = [i for i in report.issues if i.code == IssueCode.NO_TITLE_PAGE]
        assert len(tp_issues) == 1
        assert tp_issues[0].severity == Severity.ERROR

    def test_default_title_produces_warning(self):
        doc = _make_doc(body_text="Content.")
        doc.title_page = TitlePageData()  # defaults: "Documento sin título"
        report = ExportValidator().validate(doc)
        tp_issues = [i for i in report.issues if i.code == IssueCode.NO_TITLE_PAGE]
        assert len(tp_issues) >= 1
        assert any(i.severity == Severity.WARNING for i in tp_issues)

    def test_complete_title_page_no_issues(self):
        doc = _make_doc(body_text="Content.")
        doc.title_page = TitlePageData(title="Mi Investigación", authors=["Juan Pérez"])
        report = ExportValidator().validate(doc)
        tp_issues = [i for i in report.issues if i.code == IssueCode.NO_TITLE_PAGE]
        assert len(tp_issues) == 0


class TestAbstractTooLong:
    """ABSTRACT_TOO_LONG: abstract > 250 words."""

    def test_long_abstract_produces_warning(self):
        long_abstract = " ".join(["word"] * 300)
        doc = _make_doc(abstract=long_abstract)
        report = ExportValidator().validate(doc)
        ab_issues = [i for i in report.issues if i.code == IssueCode.ABSTRACT_TOO_LONG]
        assert len(ab_issues) == 1
        assert ab_issues[0].severity == Severity.WARNING
        assert "300" in ab_issues[0].message

    def test_normal_abstract_no_warning(self):
        normal = " ".join(["word"] * 200)
        doc = _make_doc(abstract=normal)
        report = ExportValidator().validate(doc)
        ab_issues = [i for i in report.issues if i.code == IssueCode.ABSTRACT_TOO_LONG]
        assert len(ab_issues) == 0

    def test_no_abstract_no_warning(self):
        doc = _make_doc()
        report = ExportValidator().validate(doc)
        ab_issues = [i for i in report.issues if i.code == IssueCode.ABSTRACT_TOO_LONG]
        assert len(ab_issues) == 0


class TestEmptyParagraphs:
    """EMPTY_PARAGRAPHS: empty sections or multiple blank lines."""

    def test_empty_section_produces_warning(self):
        sections = [Section(heading="Introduction", content="")]
        doc = _make_doc(sections=sections)
        report = ExportValidator().validate(doc)
        ep = [i for i in report.issues if i.code == IssueCode.EMPTY_PARAGRAPHS]
        assert len(ep) == 1
        assert "Introduction" in ep[0].message

    def test_multiple_blank_lines_detected(self):
        sections = [Section(heading="Body", content="First paragraph.\n\n\n\nSecond paragraph.")]
        doc = _make_doc(sections=sections)
        report = ExportValidator().validate(doc)
        ep = [i for i in report.issues if i.code == IssueCode.EMPTY_PARAGRAPHS]
        assert len(ep) == 1
        assert "saltos de línea" in ep[0].message

    def test_normal_content_no_warning(self):
        sections = [Section(heading="Body", content="Normal content.")]
        doc = _make_doc(sections=sections)
        report = ExportValidator().validate(doc)
        ep = [i for i in report.issues if i.code == IssueCode.EMPTY_PARAGRAPHS]
        assert len(ep) == 0


class TestNoReferences:
    """NO_REFERENCES: citations exist but no refs section."""

    def test_citations_without_refs_is_error(self):
        doc = _make_doc(
            body_text="According to (Smith, 2020) this is true.",
            refs=[],
        )
        report = ExportValidator().validate(doc)
        nr = [i for i in report.issues if i.code == IssueCode.NO_REFERENCES]
        assert len(nr) == 1
        assert nr[0].severity == Severity.ERROR

    def test_no_citations_no_refs_is_fine(self):
        doc = _make_doc(body_text="Plain text with no citations.", refs=[])
        report = ExportValidator().validate(doc)
        nr = [i for i in report.issues if i.code == IssueCode.NO_REFERENCES]
        assert len(nr) == 0


# ===================================================================
# 4. ValidationReport Properties
# ===================================================================


class TestValidationReport:
    def test_is_blocking_with_error(self):
        report = ValidationReport(
            issues=[
                ValidationIssue(Severity.ERROR, IssueCode.CITE_ORPHAN, "x"),
                ValidationIssue(Severity.WARNING, IssueCode.REF_UNCITED, "y"),
            ]
        )
        assert report.is_blocking is True

    def test_not_blocking_with_warnings_only(self):
        report = ValidationReport(
            issues=[
                ValidationIssue(Severity.WARNING, IssueCode.REF_UNCITED, "y"),
            ]
        )
        assert report.is_blocking is False

    def test_is_clean_when_empty(self):
        report = ValidationReport()
        assert report.is_clean is True

    def test_errors_property(self):
        report = ValidationReport(
            issues=[
                ValidationIssue(Severity.ERROR, IssueCode.CITE_ORPHAN, "x"),
                ValidationIssue(Severity.WARNING, IssueCode.REF_UNCITED, "y"),
            ]
        )
        assert len(report.errors) == 1
        assert len(report.warnings) == 1


# ===================================================================
# 5. SmartExportManager Orchestration
# ===================================================================


class TestSmartExportManager:
    def _mock_renderer(self, return_path: Path | None = None):
        renderer = MagicMock()
        renderer.render.return_value = return_path or Path("/tmp/output.docx")
        return renderer

    def _clean_doc(self) -> tuple[APADocument, SemanticDocument]:
        """Build a clean doc pair (no validation issues)."""
        sem = _make_doc(body_text="No citations here.")
        apa = MagicMock(spec=APADocument)
        return apa, sem

    def _blocking_doc(self) -> tuple[APADocument, SemanticDocument]:
        """Build a doc that will trigger blocking errors."""
        sem = _make_doc(
            body_text="According to (Unknown, 2025) this is wrong.",
            refs=[],
        )
        apa = MagicMock(spec=APADocument)
        return apa, sem

    def _warning_doc(self) -> tuple[APADocument, SemanticDocument]:
        """Build a doc that triggers only warnings."""
        sem = _make_doc(
            body_text="Smith (2020) demonstrated this.",
            refs=[_make_ref("Smith", 2020), _make_ref("Extra", 2019)],
        )
        apa = MagicMock(spec=APADocument)
        return apa, sem

    # -- Tests ---------------------------------------------------------------

    def test_clean_export_renders(self):
        renderer = self._mock_renderer()
        manager = SmartExportManager(renderer=renderer)
        apa, sem = self._clean_doc()

        result = manager.execute(apa, sem, Path("/tmp/out.docx"))

        assert not result.blocked
        assert result.output_path is not None
        renderer.render.assert_called_once()

    def test_blocking_errors_abort_render(self):
        renderer = self._mock_renderer()
        manager = SmartExportManager(renderer=renderer)
        apa, sem = self._blocking_doc()

        result = manager.execute(apa, sem, Path("/tmp/out.docx"))

        assert result.blocked
        assert result.output_path is None
        renderer.render.assert_not_called()

    def test_warnings_do_not_block(self):
        renderer = self._mock_renderer()
        manager = SmartExportManager(renderer=renderer)
        apa, sem = self._warning_doc()

        result = manager.execute(apa, sem, Path("/tmp/out.docx"))

        assert not result.blocked
        assert result.output_path is not None
        assert len(result.report.warnings) >= 1
        renderer.render.assert_called_once()

    def test_force_export_bypasses_validation(self):
        renderer = self._mock_renderer()
        manager = SmartExportManager(renderer=renderer)
        apa, _ = self._blocking_doc()

        result = manager.force_export(apa, Path("/tmp/out.docx"))

        assert not result.blocked
        assert result.output_path is not None
        renderer.render.assert_called_once()

    def test_validate_only_does_not_render(self):
        renderer = self._mock_renderer()
        manager = SmartExportManager(renderer=renderer)
        _, sem = self._blocking_doc()

        report = manager.validate_only(sem)

        assert report.is_blocking
        renderer.render.assert_not_called()

    def test_export_result_dataclass(self):
        result = ExportResult(
            report=ValidationReport(),
            blocked=False,
            output_path=Path("/tmp/out.docx"),
        )
        assert result.output_path == Path("/tmp/out.docx")
        assert not result.blocked
