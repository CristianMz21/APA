"""Port: Metadata fetcher — retrieve reference info from external sources."""

from abc import ABC, abstractmethod

from apa_formatter.domain.models.reference import Reference


class MetadataFetcherPort(ABC):
    """Contract for fetching reference metadata (DOI, ISBN, URL)."""

    @abstractmethod
    def fetch(self, identifier: str) -> Reference:
        """Fetch metadata and return a populated Reference.

        Args:
            identifier: DOI string, ISBN, or URL depending on implementation.

        Raises:
            MetadataFetchError: If the fetch fails.
        """
        ...
