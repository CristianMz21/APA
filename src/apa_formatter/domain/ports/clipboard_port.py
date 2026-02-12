"""Port: Clipboard — copy text to system clipboard."""

from abc import ABC, abstractmethod


class ClipboardPort(ABC):
    """Contract for clipboard operations."""

    @abstractmethod
    def copy(self, text: str) -> None:
        """Copy the given text to the system clipboard.

        Raises:
            ClipboardError: If no clipboard backend is available.
        """
        ...
