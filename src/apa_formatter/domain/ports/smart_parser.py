"""Port for parsing raw text into Reference objects."""

from abc import ABC, abstractmethod

from apa_formatter.domain.models.reference import Reference


class SmartParserPort(ABC):
    """Interface for converting raw strings into structured References."""

    @abstractmethod
    def parse(self, text: str) -> Reference | None:
        """Attempt to parse text into a Reference.

        Returns None if parsing fails completely.
        """
        ...
