"""Port: Reference repository — save/load reference collections."""

from abc import ABC, abstractmethod
from pathlib import Path

from apa_formatter.domain.models.reference import Reference


class ReferenceRepositoryPort(ABC):
    """Contract for persisting and retrieving references."""

    @abstractmethod
    def save(self, references: list[Reference], path: Path) -> None:
        """Save a list of references to the given path."""
        ...

    @abstractmethod
    def load(self, path: Path) -> list[Reference]:
        """Load a list of references from the given path."""
        ...
