"""Tests for APA checker and converter."""

import pytest

from apa_formatter.adapters.docx_adapter import DocxAdapter
from apa_formatter.converters import docx_to_pdf
from apa_formatter.models.document import (
    APADocument,
    Author,
    Reference,
    Section,
    TitlePage,
)
from apa_formatter.models.enums import ReferenceType
from apa_formatter.validators.checker import APAChecker, CheckResult, ComplianceReport


# ---------------------------------------------------------------------------
# APAChecker
# ---------------------------------------------------------------------------


class TestAPAChecker:
    @pytest.fixture
    def apa_docx(self, tmp_path):
        """Generate a proper APA-formatted .docx file for checking."""
        doc = APADocument(
            title_page=TitlePage(
                title="Test Paper",
                authors=["Test Author"],
                affiliation="Test University",
            ),
            abstract="Test abstract.",
            sections=[
                Section(heading="Introduction", content="Test content."),
            ],
            references=[
                Reference(
                    ref_type=ReferenceType.JOURNAL_ARTICLE,
                    authors=[Author(last_name="Smith", first_name="J")],
                    year=2023,
                    title="Test",
                    source="Journal",
                ),
            ],
        )
        output = tmp_path / "test.docx"
        adapter = DocxAdapter(doc)
        adapter.generate(output)
        return output

    def test_check_apa_document_passes(self, apa_docx):
        checker = APAChecker(apa_docx)
        report = checker.check()
        assert isinstance(report, ComplianceReport)
        assert report.total > 0
        assert report.score > 50

    def test_check_margin_results(self, apa_docx):
        checker = APAChecker(apa_docx)
        report = checker.check()
        margin_results = [r for r in report.results if "margin" in r.rule.lower()]
        assert len(margin_results) == 4  # top, bottom, left, right
        assert all(r.passed for r in margin_results)

    def test_check_font_results(self, apa_docx):
        checker = APAChecker(apa_docx)
        report = checker.check()
        font_results = [r for r in report.results if "font" in r.rule.lower()]
        assert len(font_results) >= 2

    def test_check_spacing_results(self, apa_docx):
        checker = APAChecker(apa_docx)
        report = checker.check()
        spacing_results = [r for r in report.results if "spacing" in r.rule.lower()]
        assert len(spacing_results) >= 1

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            APAChecker(tmp_path / "nonexistent.docx")

    def test_wrong_format(self, tmp_path):
        bad = tmp_path / "test.pdf"
        bad.touch()
        with pytest.raises(ValueError, match="Unsupported format"):
            APAChecker(bad)

    def test_high_compliance_score(self, apa_docx):
        """An APA-generated document should score high on compliance."""
        checker = APAChecker(apa_docx)
        report = checker.check()
        assert report.score >= 70  # Should be mostly compliant
        assert report.is_compliant

    def test_compliance_report_properties(self):
        report = ComplianceReport(
            file_path="test.docx",
            results=[
                CheckResult(rule="Test 1", passed=True, expected="A", actual="A"),
                CheckResult(
                    rule="Test 2", passed=False, expected="B", actual="C", severity="error"
                ),
                CheckResult(rule="Test 3", passed=True, expected="D", actual="D"),
            ],
        )
        assert report.total == 3
        assert report.passed == 2
        assert report.failed == 1
        assert report.score == pytest.approx(66.67, abs=0.1)
        assert report.is_compliant is False  # One error severity failure

    def test_check_result_icons(self):
        assert CheckResult(rule="r", passed=True, expected="", actual="").icon == "✅"
        assert (
            CheckResult(rule="r", passed=False, expected="", actual="", severity="error").icon
            == "❌"
        )
        assert (
            CheckResult(rule="r", passed=False, expected="", actual="", severity="warning").icon
            == "⚠️"
        )


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


class TestConverter:
    @pytest.fixture
    def source_docx(self, tmp_path):
        """Generate a .docx file to convert."""
        doc = APADocument(
            title_page=TitlePage(
                title="Conversion Test Paper",
                authors=["Jane Doe"],
                affiliation="MIT",
            ),
            abstract="Abstract for conversion.",
            sections=[
                Section(heading="Introduction", content="Body text for testing."),
                Section(heading="Method", content="Method description."),
            ],
        )
        output = tmp_path / "source.docx"
        adapter = DocxAdapter(doc)
        adapter.generate(output)
        return output

    def test_docx_to_pdf_creates_output(self, source_docx, tmp_path):
        output = tmp_path / "converted.pdf"
        result = docx_to_pdf(source_docx, output)
        assert result.exists()
        assert result.suffix == ".pdf"
        assert result.stat().st_size > 0

    def test_docx_to_pdf_default_name(self, source_docx, tmp_path):
        output = tmp_path / "output.pdf"
        result = docx_to_pdf(source_docx, output)
        assert result.name == "output.pdf"

    def test_source_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            docx_to_pdf(tmp_path / "missing.docx", tmp_path / "out.pdf")
