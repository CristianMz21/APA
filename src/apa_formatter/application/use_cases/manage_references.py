"""Use Case: Manage References.

CRUD operations on a reference collection, persisted via ReferenceRepositoryPort.
"""

from pathlib import Path

from apa_formatter.domain.errors import ReferenceNotFoundError
from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.models.reference_manager import ReferenceManager
from apa_formatter.domain.ports.reference_repository import ReferenceRepositoryPort


class ManageReferencesUseCase:
    """CRUD + persistence for a reference collection."""

    def __init__(self, repository: ReferenceRepositoryPort) -> None:
        self._repository = repository
        self._manager = ReferenceManager()

    # -- Persistence ---------------------------------------------------------

    def load(self, path: Path) -> list[Reference]:
        """Load references from storage."""
        refs = self._repository.load(path)
        self._manager = ReferenceManager(references=refs)
        self._manager.disambiguate_years()
        return self._manager.references

    def save(self, path: Path) -> None:
        """Save current references to storage."""
        self._repository.save(self._manager.references, path)

    # -- CRUD ----------------------------------------------------------------

    def add(self, ref: Reference) -> None:
        """Add a reference (triggers disambiguation)."""
        self._manager.add(ref)

    def remove(self, index: int) -> None:
        """Remove a reference by index."""
        if index < 0 or index >= len(self._manager.references):
            raise ReferenceNotFoundError(f"No reference at index {index}.")
        self._manager.remove(index)

    def list_all(self, locale: dict[str, str] | None = None) -> str:
        """Return the sorted, formatted reference list."""
        return self._manager.format_reference_list(locale)

    @property
    def references(self) -> list[Reference]:
        """Access the current list of references."""
        return self._manager.references
