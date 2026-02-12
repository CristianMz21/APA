"""Port: Document renderer — generates formatted output files.

This is a domain-level contract. Infrastructure adapters (docx, pdf)
implement this interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from apa_formatter.domain.models.document import APADocument


class DocumentRendererPort(ABC):
    """Contract for rendering an APA document to a file."""

    @abstractmethod
    def render(self, document: APADocument, output_path: Path) -> Path:
        """Generate the formatted document and return the output path."""
        ...
