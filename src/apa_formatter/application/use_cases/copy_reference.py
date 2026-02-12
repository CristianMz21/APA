"""Use Case: Copy Reference to Clipboard.

Formats a reference in APA 7 and copies it to the system clipboard
through an injected ClipboardPort.
"""

from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.ports.clipboard_port import ClipboardPort


class CopyReferenceUseCase:
    """Format and copy a reference to the clipboard."""

    def __init__(self, clipboard: ClipboardPort) -> None:
        self._clipboard = clipboard

    def execute(
        self,
        reference: Reference,
        locale: dict[str, str] | None = None,
    ) -> str:
        """Format the reference and copy it.

        Args:
            reference: The reference to format and copy.
            locale: Optional locale dict for formatting.

        Returns:
            The formatted reference string that was copied.
        """
        formatted = reference.format_apa(locale)
        self._clipboard.copy(formatted)
        return formatted
