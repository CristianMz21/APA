"""Use Case: Convert Document between formats.

Orchestrates document conversion (e.g., DOCX → PDF).
"""

from pathlib import Path

from apa_formatter.domain.errors import DocumentGenerationError
from apa_formatter.domain.models.document import APADocument
from apa_formatter.domain.ports.document_renderer import DocumentRendererPort


class ConvertDocumentUseCase:
    """Convert a document to a different format.

    The use case receives the target renderer and an already-parsed
    APADocument from the source file.
    """

    def __init__(self, target_renderer: DocumentRendererPort) -> None:
        self._renderer = target_renderer

    def execute(self, document: APADocument, output_path: Path) -> Path:
        """Render the document using the target format renderer.

        Args:
            document: The parsed document from the source file.
            output_path: Target output file path.

        Returns:
            Path to the generated file.

        Raises:
            DocumentGenerationError: If conversion fails.
        """
        try:
            return self._renderer.render(document, output_path)
        except Exception as exc:
            raise DocumentGenerationError(f"Conversion failed: {exc}") from exc
