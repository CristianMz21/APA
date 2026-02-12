"""Tests for Sprint 3: DOI validation and metadata fetchers (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from apa_formatter.models.document import Reference
from apa_formatter.models.enums import ReferenceType
from apa_formatter.fetchers.isbn_fetcher import (
    ISBNFetchError,
    ISBNNotFoundError,
    fetch_by_isbn,
)
from apa_formatter.fetchers.doi_fetcher import (
    DOIFetchError,
    DOINotFoundError,
    fetch_by_doi,
    normalize_doi,
    validate_doi,
)
from apa_formatter.fetchers.url_fetcher import URLFetchError, fetch_by_url


# ===========================================================================
# DOI Validation on Reference model
# ===========================================================================


class TestDOIValidation:
    """Reference.doi field_validator normalizes and validates DOIs."""

    def test_valid_bare_doi(self):
        ref = Reference(ref_type=ReferenceType.JOURNAL_ARTICLE, doi="10.1037/amp0000722")
        assert ref.doi == "10.1037/amp0000722"

    def test_strips_doi_url_prefix(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            doi="https://doi.org/10.1037/amp0000722",
        )
        assert ref.doi == "10.1037/amp0000722"

    def test_strips_dx_doi_prefix(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            doi="http://dx.doi.org/10.1037/amp0000722",
        )
        assert ref.doi == "10.1037/amp0000722"

    def test_invalid_doi_raises(self):
        with pytest.raises(ValidationError, match="Invalid DOI format"):
            Reference(ref_type=ReferenceType.JOURNAL_ARTICLE, doi="not-a-doi")

    def test_none_doi_allowed(self):
        ref = Reference(ref_type=ReferenceType.BOOK)
        assert ref.doi is None

    def test_complex_doi(self):
        doi = "10.1002/(SICI)1097-4679(199911)55:11<1381::AID-JCLP7>3.0.CO;2-1"
        ref = Reference(ref_type=ReferenceType.JOURNAL_ARTICLE, doi=doi)
        assert ref.doi == doi


# ===========================================================================
# DOI utility functions
# ===========================================================================


class TestDOIUtils:
    def test_normalize_strips_url(self):
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"

    def test_normalize_bare(self):
        assert normalize_doi("10.1234/test") == "10.1234/test"

    def test_validate_valid(self):
        assert validate_doi("10.1037/amp0000722") is True

    def test_validate_invalid(self):
        assert validate_doi("not-a-doi") is False


# ===========================================================================
# ISBN Fetcher (mocked)
# ===========================================================================


class TestISBNFetcher:
    @patch("apa_formatter.fetchers.isbn_fetcher.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ISBN:9780134685991": {
                "title": "Effective Java",
                "authors": [{"name": "Joshua Bloch"}],
                "publish_date": "2018",
                "publishers": [{"name": "Addison-Wesley"}],
                "url": "https://openlibrary.org/books/OL123",
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ref = fetch_by_isbn("978-0-13-468599-1")
        assert ref.title == "Effective Java"
        assert ref.year == 2018
        assert ref.source == "Addison-Wesley"
        assert ref.ref_type == ReferenceType.BOOK
        assert len(ref.authors) == 1
        assert ref.authors[0].last_name == "Bloch"

    @patch("apa_formatter.fetchers.isbn_fetcher.requests.get")
    def test_isbn_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(ISBNNotFoundError):
            fetch_by_isbn("0000000000")

    @patch("apa_formatter.fetchers.isbn_fetcher.requests.get")
    def test_network_error(self, mock_get):
        import requests as req

        mock_get.side_effect = req.ConnectionError("offline")

        with pytest.raises(ISBNFetchError, match="request failed"):
            fetch_by_isbn("9780134685991")


# ===========================================================================
# DOI Fetcher (mocked)
# ===========================================================================


class TestDOIFetcher:
    @patch("apa_formatter.fetchers.doi_fetcher.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "author": [
                    {"given": "John", "family": "Smith"},
                    {"given": "Jane", "family": "Doe"},
                ],
                "title": ["Test Article Title"],
                "container-title": ["Journal of Testing"],
                "published-print": {"date-parts": [[2020]]},
                "volume": "15",
                "issue": "3",
                "page": "100-115",
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ref = fetch_by_doi("10.1234/test.2020")
        assert ref.title == "Test Article Title"
        assert ref.year == 2020
        assert ref.source == "Journal of Testing"
        assert ref.volume == "15"
        assert ref.issue == "3"
        assert ref.pages == "100-115"
        assert ref.doi == "10.1234/test.2020"
        assert len(ref.authors) == 2
        assert ref.authors[0].last_name == "Smith"

    @patch("apa_formatter.fetchers.doi_fetcher.requests.get")
    def test_doi_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with pytest.raises(DOINotFoundError):
            fetch_by_doi("10.9999/nonexistent")

    @patch("apa_formatter.fetchers.doi_fetcher.requests.get")
    def test_network_error(self, mock_get):
        import requests as req

        mock_get.side_effect = req.ConnectionError("offline")

        with pytest.raises(DOIFetchError, match="request failed"):
            fetch_by_doi("10.1234/test")

    @patch("apa_formatter.fetchers.doi_fetcher.requests.get")
    def test_auto_normalizes_doi_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "author": [],
                "title": ["Test"],
                "container-title": [],
                "published-print": {"date-parts": [[2021]]},
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetch_by_doi("https://doi.org/10.1234/test")
        # Ensure the CrossRef URL used bare DOI
        call_url = mock_get.call_args[0][0]
        assert call_url == "https://api.crossref.org/works/10.1234/test"


# ===========================================================================
# URL Fetcher (mocked)
# ===========================================================================


class TestURLFetcher:
    @patch("apa_formatter.fetchers.url_fetcher.requests.get")
    def test_successful_fetch(self, mock_get):
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta property="og:title" content="OG Title" />
            <meta name="author" content="John Smith" />
            <meta property="og:site_name" content="Test Site" />
            <meta name="date" content="2023-01-15" />
        </head>
        <body></body>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ref = fetch_by_url("https://example.com/article")
        assert ref.title == "OG Title"
        assert ref.source == "Test Site"
        assert ref.year == 2023
        assert ref.url == "https://example.com/article"
        assert ref.ref_type == ReferenceType.WEBPAGE
        assert len(ref.authors) == 1
        assert ref.authors[0].last_name == "Smith"

    @patch("apa_formatter.fetchers.url_fetcher.requests.get")
    def test_fallback_to_title_tag(self, mock_get):
        html = "<html><head><title>Fallback Title</title></head></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ref = fetch_by_url("https://example.com")
        assert ref.title == "Fallback Title"
        assert len(ref.authors) == 0

    @patch("apa_formatter.fetchers.url_fetcher.requests.get")
    def test_network_error(self, mock_get):
        import requests as req

        mock_get.side_effect = req.ConnectionError("offline")

        with pytest.raises(URLFetchError, match="Failed to fetch"):
            fetch_by_url("https://example.com")

    @patch("apa_formatter.fetchers.url_fetcher.requests.get")
    def test_retrieval_date_set(self, mock_get):
        from datetime import date

        html = "<html><head><title>T</title></head></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ref = fetch_by_url("https://example.com")
        assert ref.retrieval_date == date.today()
