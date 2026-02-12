"""Use Case: Fetch Metadata from external sources.

Orchestrates metadata retrieval (DOI, ISBN, URL) through injected ports.
"""

from apa_formatter.domain.errors import MetadataFetchError
from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.ports.metadata_fetcher import MetadataFetcherPort


class FetchMetadataUseCase:
    """Fetch reference metadata from an external source."""

    def __init__(self, fetcher: MetadataFetcherPort) -> None:
        self._fetcher = fetcher

    def execute(self, identifier: str) -> Reference:
        """Fetch metadata and return a populated Reference.

        Args:
            identifier: DOI, ISBN, or URL depending on the fetcher.

        Returns:
            A populated Reference domain entity.

        Raises:
            MetadataFetchError: If the fetch fails.
        """
        try:
            return self._fetcher.fetch(identifier)
        except Exception as exc:
            raise MetadataFetchError(f"Failed to fetch metadata for '{identifier}': {exc}") from exc
