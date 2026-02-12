"""DOI fetcher — implements MetadataFetcherPort via CrossRef API.

Wraps the existing fetchers/doi_fetcher.py module.
"""

from apa_formatter.domain.errors import MetadataFetchError
from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.ports.metadata_fetcher import MetadataFetcherPort


class DoiFetcher(MetadataFetcherPort):
    """Fetch article metadata from CrossRef by DOI."""

    def fetch(self, identifier: str) -> Reference:
        """Fetch metadata by DOI.

        Args:
            identifier: A DOI string (bare or URL).

        Returns:
            A populated Reference.

        Raises:
            MetadataFetchError: If fetch fails.
        """
        from apa_formatter.fetchers.doi_fetcher import fetch_by_doi

        try:
            return fetch_by_doi(identifier)
        except Exception as exc:
            raise MetadataFetchError(f"DOI fetch failed for '{identifier}': {exc}") from exc
