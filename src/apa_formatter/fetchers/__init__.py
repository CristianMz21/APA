"""Metadata fetchers for auto-populating APA references from ISBN, DOI, or URL."""

from apa_formatter.fetchers.isbn_fetcher import fetch_by_isbn
from apa_formatter.fetchers.doi_fetcher import fetch_by_doi
from apa_formatter.fetchers.url_fetcher import fetch_by_url

__all__ = ["fetch_by_isbn", "fetch_by_doi", "fetch_by_url"]
