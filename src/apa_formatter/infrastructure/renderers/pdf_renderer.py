"""PDF renderer — implements DocumentRendererPort using fpdf2.

Thin wrapper around the existing PdfAdapter.
"""

from pathlib import Path

from apa_formatter.domain.models.document import APADocument
from apa_formatter.domain.ports.document_renderer import DocumentRendererPort


class PdfRenderer(DocumentRendererPort):
    """Render APA 7 documents as PDF files."""

    def __init__(self, config=None) -> None:
        self._config = config

    def render(self, document: APADocument, output_path: Path) -> Path:
        """Generate a PDF via the legacy adapter."""
        from apa_formatter.adapters.pdf_adapter import PdfAdapter

        adapter = PdfAdapter(document, config=self._config)
        return adapter.generate(output_path)
