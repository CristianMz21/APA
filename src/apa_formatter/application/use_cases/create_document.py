"""Use Case: Create Document.

Orchestrates document creation through an injected renderer port.
"""

from pathlib import Path

from apa_formatter.domain.errors import DocumentGenerationError
from apa_formatter.domain.models.document import APADocument
from apa_formatter.domain.ports.document_renderer import DocumentRendererPort


class CreateDocumentUseCase:
    """Orchestrate document creation through an injected renderer."""

    def __init__(self, renderer: DocumentRendererPort) -> None:
        self._renderer = renderer

    def execute(self, document: APADocument, output_path: Path) -> Path:
        """Validate the document and delegate rendering to infrastructure.

        Args:
            document: The fully populated APA document model.
            output_path: Where to write the output file.

        Returns:
            The final path to the generated file.

        Raises:
            DocumentGenerationError: If rendering fails.
        """
        if not document.title_page:
            raise DocumentGenerationError("A title page is required.")

        try:
            return self._renderer.render(document, output_path)
        except Exception as exc:
            raise DocumentGenerationError(f"Failed to generate document: {exc}") from exc
