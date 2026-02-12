"""Tests for the SmartReferenceParser."""

import pytest
from unittest.mock import MagicMock

from apa_formatter.infrastructure.importers.smart_parser import SmartReferenceParser
from apa_formatter.domain.models.reference import Reference, Author
from apa_formatter.domain.models.enums import ReferenceType
from datetime import date


@pytest.fixture
def parser():
    """Fixture for SmartReferenceParser with mocked fetchers."""
    p = SmartReferenceParser()
    p._doi_fetcher = MagicMock()
    p._isbn_fetcher = MagicMock()
    p._url_fetcher = MagicMock()
    return p


def test_deterministic_doi(parser):
    """Test DOI detection and delegation."""
    text = "Here is a paper: 10.1037/0000092-001 check it out."
    expected_ref = Reference(
        ref_type=ReferenceType.JOURNAL_ARTICLE,
        authors=[Author(first_name="Test", last_name="Author")],
        year=2023,
        title="Test DOI",
        source="Journal",
        retrieval_date=date.today(),
    )
    parser._doi_fetcher.fetch.return_value = expected_ref

    result = parser.parse(text)

    assert result == expected_ref
    parser._doi_fetcher.fetch.assert_called_once_with("10.1037/0000092-001")


def test_deterministic_isbn(parser):
    """Test ISBN detection and delegation."""
    text = "Read the book ISBN 978-3-16-148410-0 for more info."
    expected_ref = Reference(
        ref_type=ReferenceType.BOOK,
        authors=[Author(first_name="Book", last_name="Writer")],
        year=2020,
        title="Test Book",
        source="Publisher",
        retrieval_date=date.today(),
    )
    parser._isbn_fetcher.fetch.return_value = expected_ref

    result = parser.parse(text)

    assert result == expected_ref
    parser._isbn_fetcher.fetch.assert_called_once_with("9783161484100")


def test_deterministic_url(parser):
    """Test URL detection and delegation."""
    text = "See https://example.com/article for details."
    expected_ref = Reference(
        ref_type=ReferenceType.WEBPAGE,
        authors=[Author(first_name="Web", last_name="Author")],
        year=2023,
        title="Web Page",
        source="Example",
        retrieval_date=date.today(),
    )
    parser._url_fetcher.fetch.return_value = expected_ref

    result = parser.parse(text)

    assert result == expected_ref
    parser._url_fetcher.fetch.assert_called_once_with("https://example.com/article")


def test_bibtex_parsing(parser):
    """Test BibTeX parsing strategy."""
    text = """
    @article{sample,
        author = {Smith, John and Doe, Jane},
        title = {A Great Paper},
        year = {2023},
        publisher = {Science Journal}
    }
    """

    result = parser.parse(text)

    assert result is not None
    assert result.title == "A Great Paper"
    assert result.year == 2023
    assert len(result.authors) == 2
    assert result.authors[0].last_name == "Smith"
    assert result.authors[1].last_name == "Doe"


def test_heuristic_parsing_fallback(parser):
    """Test heuristic parsing for unstructured text."""
    text = "Freud, S. (1900). The Interpretation of Dreams."

    result = parser.parse(text)

    assert result is not None
    assert result.year == 1900
    assert result.authors[0].last_name == "Freud"


def test_empty_input(parser):
    """Test empty input returns None."""
    assert parser.parse("") is None
    assert parser.parse("   ") is None
