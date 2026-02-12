"""URL fetcher — implements MetadataFetcherPort for web pages.

Wraps the existing fetchers/url_fetcher.py module.
"""

from apa_formatter.domain.errors import MetadataFetchError
from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.ports.metadata_fetcher import MetadataFetcherPort


class UrlFetcher(MetadataFetcherPort):
    """Fetch web page metadata by URL (title, author from meta tags)."""

    def fetch(self, identifier: str) -> Reference:
        """Fetch metadata from a URL.

        Args:
            identifier: A web URL.

        Returns:
            A populated Reference.

        Raises:
            MetadataFetchError: If fetch fails.
        """
        from apa_formatter.fetchers.url_fetcher import fetch_by_url

        try:
            return fetch_by_url(identifier)
        except Exception as exc:
            raise MetadataFetchError(f"URL fetch failed for '{identifier}': {exc}") from exc
