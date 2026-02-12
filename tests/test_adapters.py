"""Integration tests for document generation (Word and PDF)."""

from datetime import date

import pytest

from apa_formatter.adapters.docx_adapter import DocxAdapter
from apa_formatter.adapters.pdf_adapter import PdfAdapter
from apa_formatter.models.document import (
    APADocument,
    Author,
    Reference,
    Section,
    TitlePage,
)
from apa_formatter.models.enums import (
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
    ReferenceType,
)


@pytest.fixture
def minimal_doc():
    """Minimal APA document for testing."""
    return APADocument(
        title_page=TitlePage(
            title="Test Document",
            authors=["Test Author"],
            affiliation="Test University",
        ),
        sections=[
            Section(heading="Introduction", level=HeadingLevel.LEVEL_1, content="Test content."),
        ],
    )


@pytest.fixture
def full_doc():
    """Full APA document with all features."""
    return APADocument(
        title_page=TitlePage(
            title="Full Test Document",
            authors=["Jane Doe", "John Smith"],
            affiliation="MIT",
            course="CS 101",
            instructor="Dr. Brown",
            due_date=date(2026, 2, 12),
            variant=DocumentVariant.STUDENT,
        ),
        abstract="This is a test abstract for the APA 7 document.",
        keywords=["test", "apa", "formatter"],
        sections=[
            Section(
                heading="Introduction",
                level=HeadingLevel.LEVEL_1,
                content="Introduction text.",
                subsections=[
                    Section(
                        heading="Background", level=HeadingLevel.LEVEL_2, content="Background text."
                    ),
                ],
            ),
            Section(heading="Method", level=HeadingLevel.LEVEL_1, content="Method text."),
            Section(heading="Results", level=HeadingLevel.LEVEL_1, content="Results text."),
            Section(heading="Discussion", level=HeadingLevel.LEVEL_1, content="Discussion text."),
        ],
        references=[
            Reference(
                ref_type=ReferenceType.JOURNAL_ARTICLE,
                authors=[Author(last_name="Smith", first_name="John")],
                year=2023,
                title="Test Article",
                source="Test Journal",
                volume="10",
                issue="2",
                pages="1-20",
                doi="10.1234/test",
            ),
        ],
        appendices=[
            Section(
                heading="Test Appendix", level=HeadingLevel.LEVEL_1, content="Appendix content."
            ),
        ],
        font=FontChoice.TIMES_NEW_ROMAN,
    )


@pytest.fixture
def toc_doc():
    """Document with TOC enabled."""
    return APADocument(
        title_page=TitlePage(
            title="TOC Test Document",
            authors=["Author"],
            affiliation="University",
        ),
        include_toc=True,
        sections=[
            Section(heading="Section One", level=HeadingLevel.LEVEL_1, content="Content."),
            Section(heading="Section Two", level=HeadingLevel.LEVEL_1, content="Content."),
        ],
    )


# ---------------------------------------------------------------------------
# Word (.docx) Generation Tests
# ---------------------------------------------------------------------------


class TestDocxAdapter:
    def test_generates_docx_file(self, minimal_doc, tmp_path):
        output = tmp_path / "test.docx"
        adapter = DocxAdapter(minimal_doc)
        result = adapter.generate(output)
        assert result.exists()
        assert result.suffix == ".docx"
        assert result.stat().st_size > 0

    def test_adds_suffix_if_missing(self, minimal_doc, tmp_path):
        output = tmp_path / "test"
        adapter = DocxAdapter(minimal_doc)
        result = adapter.generate(output)
        assert result.suffix == ".docx"

    def test_full_document_generation(self, full_doc, tmp_path):
        output = tmp_path / "full.docx"
        adapter = DocxAdapter(full_doc)
        result = adapter.generate(output)
        assert result.exists()
        assert result.stat().st_size > 5000  # Full doc should be reasonably large

    def test_with_toc(self, toc_doc, tmp_path):
        output = tmp_path / "toc.docx"
        adapter = DocxAdapter(toc_doc)
        result = adapter.generate(output)
        assert result.exists()

    def test_professional_variant(self, tmp_path):
        doc = APADocument(
            title_page=TitlePage(
                title="Professional Paper",
                authors=["Dr. Smith"],
                affiliation="Harvard",
                variant=DocumentVariant.PROFESSIONAL,
                running_head="AI EDUCATION",
            ),
            sections=[Section(heading="Intro", content="Text.")],
        )
        output = tmp_path / "pro.docx"
        adapter = DocxAdapter(doc)
        result = adapter.generate(output)
        assert result.exists()

    def test_all_heading_levels(self, tmp_path):
        doc = APADocument(
            title_page=TitlePage(title="Heading Test", authors=["Author"], affiliation="Uni"),
            sections=[
                Section(
                    heading="Level 1",
                    level=HeadingLevel.LEVEL_1,
                    content="L1 text.",
                    subsections=[
                        Section(
                            heading="Level 2",
                            level=HeadingLevel.LEVEL_2,
                            content="L2 text.",
                            subsections=[
                                Section(
                                    heading="Level 3",
                                    level=HeadingLevel.LEVEL_3,
                                    content="L3 text.",
                                    subsections=[
                                        Section(
                                            heading="Level 4",
                                            level=HeadingLevel.LEVEL_4,
                                            content="L4 text.",
                                        ),
                                        Section(
                                            heading="Level 5",
                                            level=HeadingLevel.LEVEL_5,
                                            content="L5 text.",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        adapter = DocxAdapter(doc)
        result = adapter.generate(tmp_path / "headings.docx")
        assert result.exists()

    @pytest.mark.parametrize("font", list(FontChoice))
    def test_all_fonts(self, font, tmp_path):
        doc = APADocument(
            title_page=TitlePage(title="Font Test", authors=["Author"], affiliation="Uni"),
            sections=[Section(heading="Test", content="Content.")],
            font=font,
        )
        adapter = DocxAdapter(doc)
        result = adapter.generate(tmp_path / f"font_{font.value}.docx")
        assert result.exists()


# ---------------------------------------------------------------------------
# PDF Generation Tests
# ---------------------------------------------------------------------------


class TestPdfAdapter:
    def test_generates_pdf_file(self, minimal_doc, tmp_path):
        minimal_doc.output_format = OutputFormat.PDF
        output = tmp_path / "test.pdf"
        adapter = PdfAdapter(minimal_doc)
        result = adapter.generate(output)
        assert result.exists()
        assert result.suffix == ".pdf"
        assert result.stat().st_size > 0

    def test_adds_suffix_if_missing(self, minimal_doc, tmp_path):
        minimal_doc.output_format = OutputFormat.PDF
        output = tmp_path / "test"
        adapter = PdfAdapter(minimal_doc)
        result = adapter.generate(output)
        assert result.suffix == ".pdf"

    def test_full_document_generation(self, full_doc, tmp_path):
        full_doc.output_format = OutputFormat.PDF
        output = tmp_path / "full.pdf"
        adapter = PdfAdapter(full_doc)
        result = adapter.generate(output)
        assert result.exists()
        assert result.stat().st_size > 1000

    @pytest.mark.parametrize("font", list(FontChoice))
    def test_all_fonts(self, font, tmp_path):
        doc = APADocument(
            title_page=TitlePage(title="Font Test", authors=["Author"], affiliation="Uni"),
            sections=[Section(heading="Test", content="Content.")],
            font=font,
            output_format=OutputFormat.PDF,
        )
        adapter = PdfAdapter(doc)
        result = adapter.generate(tmp_path / f"font_{font.value}.pdf")
        assert result.exists()
