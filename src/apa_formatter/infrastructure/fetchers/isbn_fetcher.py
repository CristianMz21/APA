"""ISBN fetcher — implements MetadataFetcherPort via Open Library API.

Wraps the existing fetchers/isbn_fetcher.py module.
"""

from apa_formatter.domain.errors import MetadataFetchError
from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.ports.metadata_fetcher import MetadataFetcherPort


class IsbnFetcher(MetadataFetcherPort):
    """Fetch book metadata from Open Library by ISBN."""

    def fetch(self, identifier: str) -> Reference:
        """Fetch metadata by ISBN.

        Args:
            identifier: An ISBN-10 or ISBN-13 string.

        Returns:
            A populated Reference.

        Raises:
            MetadataFetchError: If fetch fails.
        """
        from apa_formatter.fetchers.isbn_fetcher import fetch_by_isbn

        try:
            return fetch_by_isbn(identifier)
        except Exception as exc:
            raise MetadataFetchError(f"ISBN fetch failed for '{identifier}': {exc}") from exc
