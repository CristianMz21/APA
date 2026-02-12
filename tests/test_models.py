"""Tests for APA 7 document models."""

from datetime import date

import pytest
from pydantic import ValidationError

from apa_formatter.models.document import (
    APADocument,
    Author,
    Citation,
    Reference,
    Section,
    TitlePage,
)
from apa_formatter.models.enums import (
    CitationType,
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
    ReferenceType,
)


# ---------------------------------------------------------------------------
# TitlePage
# ---------------------------------------------------------------------------


class TestTitlePage:
    def test_student_variant(self):
        tp = TitlePage(
            title="Test Paper",
            authors=["Jane Doe"],
            affiliation="MIT",
            course="PSY 101",
            instructor="Dr. Smith",
            due_date=date(2026, 1, 15),
        )
        assert tp.variant == DocumentVariant.STUDENT
        assert tp.course == "PSY 101"

    def test_professional_variant(self):
        tp = TitlePage(
            title="Test Paper",
            authors=["Jane Doe"],
            affiliation="MIT",
            variant=DocumentVariant.PROFESSIONAL,
            running_head="AI AND EDUCATION",
        )
        assert tp.variant == DocumentVariant.PROFESSIONAL
        assert tp.running_head == "AI AND EDUCATION"

    def test_running_head_max_length(self):
        with pytest.raises(ValidationError):
            TitlePage(
                title="Test",
                authors=["Author"],
                affiliation="Uni",
                running_head="X" * 51,  # exceeds 50 char limit
            )

    def test_requires_at_least_one_author(self):
        with pytest.raises(ValidationError):
            TitlePage(title="Test", authors=[], affiliation="Uni")

    def test_multiple_authors(self):
        tp = TitlePage(
            title="Test",
            authors=["Jane Doe", "John Smith", "Emily Brown"],
            affiliation="Uni",
        )
        assert len(tp.authors) == 3


# ---------------------------------------------------------------------------
# Author
# ---------------------------------------------------------------------------


class TestAuthor:
    def test_apa_format_basic(self):
        a = Author(last_name="García", first_name="Pedro")
        assert a.apa_format == "García, P."

    def test_apa_format_with_middle_initial(self):
        a = Author(last_name="López", first_name="Carmen", middle_initial="R")
        assert a.apa_format == "López, C. R."

    def test_apa_narrative(self):
        a = Author(last_name="Smith", first_name="John")
        assert a.apa_narrative == "Smith"


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


class TestReference:
    def _make_authors(self, count=1):
        return [Author(last_name=f"Author{i}", first_name=f"First{i}") for i in range(count)]

    def test_single_author(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=self._make_authors(1),
            year=2022,
            title="Test Article",
            source="Test Journal",
        )
        result = ref.format_apa()
        assert "Author0, F." in result
        assert "(2022)" in result

    def test_two_authors(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=self._make_authors(2),
            year=2023,
            title="Test",
            source="Journal",
        )
        result = ref.format_authors_apa()
        assert "&" in result

    def test_three_to_twenty_authors(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=self._make_authors(5),
            year=2023,
            title="Test",
            source="Journal",
        )
        result = ref.format_authors_apa()
        assert ", &" in result

    def test_twenty_one_plus_authors(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=self._make_authors(25),
            year=2023,
            title="Test",
            source="Journal",
        )
        result = ref.format_authors_apa()
        assert "..." in result
        # Should have first 19 + ... + last
        assert "Author0" in result
        assert "Author24" in result

    def test_no_year(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=self._make_authors(1),
            title="Test",
            source="Journal",
        )
        result = ref.format_apa()
        assert "(n.d.)" in result

    def test_journal_article_with_doi(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=self._make_authors(1),
            year=2023,
            title="Test Article",
            source="Test Journal",
            volume="15",
            issue="3",
            pages="234-256",
            doi="10.1234/test",
        )
        result = ref.format_apa()
        assert "https://doi.org/10.1234/test" in result
        assert "*Test Journal*" in result
        assert "*15*" in result

    def test_book_with_edition(self):
        ref = Reference(
            ref_type=ReferenceType.BOOK,
            authors=self._make_authors(1),
            year=2020,
            title="Test Book",
            source="Publisher",
            edition="3",
        )
        result = ref.format_apa()
        assert "*Test Book*" in result
        assert "(3 ed.)" in result

    def test_webpage(self):
        ref = Reference(
            ref_type=ReferenceType.WEBPAGE,
            authors=self._make_authors(1),
            year=2024,
            title="Test Page",
            source="Example.com",
            url="https://example.com",
        )
        result = ref.format_apa()
        assert "https://example.com" in result
        assert "Example.com" in result

    def test_no_authors(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            year=2023,
            title="Test",
            source="Journal",
        )
        result = ref.format_apa()
        assert result.startswith("(2023)")


# ---------------------------------------------------------------------------
# Citation
# ---------------------------------------------------------------------------


class TestCitation:
    def test_parenthetical_single_author(self):
        c = Citation(authors=["Smith"], year=2022)
        assert c.format_apa() == "(Smith, 2022)"

    def test_parenthetical_two_authors(self):
        c = Citation(authors=["Smith", "Jones"], year=2022)
        assert c.format_apa() == "(Smith & Jones, 2022)"

    def test_narrative_two_authors(self):
        c = Citation(
            citation_type=CitationType.NARRATIVE,
            authors=["Smith", "Jones"],
            year=2022,
        )
        assert c.format_apa() == "Smith and Jones (2022)"

    def test_three_plus_authors_et_al(self):
        c = Citation(authors=["Smith", "Jones", "Brown"], year=2023)
        assert c.format_apa() == "(Smith et al., 2023)"

    def test_with_page_number(self):
        c = Citation(authors=["Smith"], year=2022, page="45")
        assert c.format_apa() == "(Smith, 2022, p. 45)"

    def test_no_year(self):
        c = Citation(authors=["Smith"])
        assert "n.d." in c.format_apa()


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------


class TestSection:
    def test_basic_section(self):
        s = Section(heading="Introduction", content="Some text.")
        assert s.heading == "Introduction"
        assert s.level == HeadingLevel.LEVEL_1

    def test_nested_subsections(self):
        s = Section(
            heading="Method",
            level=HeadingLevel.LEVEL_1,
            subsections=[
                Section(heading="Participants", level=HeadingLevel.LEVEL_2),
                Section(heading="Procedure", level=HeadingLevel.LEVEL_2),
            ],
        )
        assert len(s.subsections) == 2
        assert s.subsections[0].level == HeadingLevel.LEVEL_2


# ---------------------------------------------------------------------------
# APADocument
# ---------------------------------------------------------------------------


class TestAPADocument:
    def _make_minimal_doc(self, **overrides):
        defaults = {
            "title_page": TitlePage(title="Test", authors=["Author"], affiliation="Uni"),
        }
        defaults.update(overrides)
        return APADocument(**defaults)

    def test_minimal_document(self):
        doc = self._make_minimal_doc()
        assert doc.font == FontChoice.TIMES_NEW_ROMAN
        assert doc.output_format == OutputFormat.DOCX

    def test_abstract_max_length(self):
        with pytest.raises(ValidationError):
            self._make_minimal_doc(abstract="X" * 2501)

    def test_include_toc_default_false(self):
        doc = self._make_minimal_doc()
        assert doc.include_toc is False

    def test_include_toc_true(self):
        doc = self._make_minimal_doc(include_toc=True)
        assert doc.include_toc is True

    def test_with_references(self):
        doc = self._make_minimal_doc(
            references=[
                Reference(
                    ref_type=ReferenceType.JOURNAL_ARTICLE,
                    authors=[Author(last_name="Smith", first_name="John")],
                    year=2023,
                    title="Test",
                    source="Journal",
                ),
            ]
        )
        assert len(doc.references) == 1

    def test_full_document(self):
        doc = self._make_minimal_doc(
            abstract="Test abstract.",
            keywords=["test", "apa"],
            sections=[
                Section(heading="Intro", content="Content."),
            ],
            font=FontChoice.CALIBRI,
            output_format=OutputFormat.PDF,
        )
        assert doc.abstract == "Test abstract."
        assert len(doc.keywords) == 2
        assert doc.font == FontChoice.CALIBRI
