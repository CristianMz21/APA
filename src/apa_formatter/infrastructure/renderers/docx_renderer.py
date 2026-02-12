"""DOCX renderer — implements DocumentRendererPort using python-docx.

This is a thin wrapper around the existing DocxAdapter. Once all consumers
migrate to the port-based approach, the adapter logic will be inlined here
and the old adapters/ package will be deleted.
"""

from pathlib import Path

from apa_formatter.domain.models.document import APADocument
from apa_formatter.domain.ports.document_renderer import DocumentRendererPort


class DocxRenderer(DocumentRendererPort):
    """Render APA 7 documents as .docx files."""

    def __init__(self, config=None) -> None:
        self._config = config

    def render(self, document: APADocument, output_path: Path) -> Path:
        """Generate a .docx file via the legacy adapter.

        Delegates to the existing DocxAdapter which contains all the
        python-docx formatting logic.
        """
        from apa_formatter.adapters.docx_adapter import DocxAdapter

        adapter = DocxAdapter(document, config=self._config)
        return adapter.generate(output_path)
