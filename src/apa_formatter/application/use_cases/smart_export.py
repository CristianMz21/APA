"""Use Case: Smart Export — pre-flight validation before rendering.

Orchestrates the export pipeline:

1. Run ``ExportValidator`` against the ``SemanticDocument``.
2. If **blocking** errors exist → return the report, **abort** rendering.
3. If only **warnings** → return the report; caller decides to force
   export or cancel.
4. If **clean** → call the renderer and return the output path + report.

Usage::

    from apa_formatter.application.use_cases.smart_export import (
        SmartExportManager,
        ExportResult,
    )

    manager = SmartExportManager(renderer=docx_renderer)
    result = manager.execute(
        document=apa_doc,
        semantic_doc=sem_doc,
        output_path=Path("output.docx"),
    )

    if result.blocked:
        show_errors(result.report)
    elif result.report.warnings:
        if user_confirms_force():
            result = manager.force_export(
                document=apa_doc, output_path=Path("output.docx")
            )
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apa_formatter.domain.errors import DocumentGenerationError
from apa_formatter.domain.models.document import APADocument
from apa_formatter.domain.ports.document_renderer import DocumentRendererPort
from apa_formatter.models.semantic_document import SemanticDocument
from apa_formatter.validators.export_validator import (
    ExportValidator,
    ValidationReport,
)


@dataclass
class ExportResult:
    """Outcome of a smart-export attempt.

    Attributes:
        report:  The full validation report.
        blocked: ``True`` if the export was aborted due to errors.
        output_path: Path to the rendered file (``None`` if blocked).
    """

    report: ValidationReport
    blocked: bool = False
    output_path: Path | None = None


class SmartExportManager:
    """Pre-flight check → render orchestrator.

    Receives a ``DocumentRendererPort`` at construction time so
    the caller can swap between DOCX / PDF renderers.
    """

    def __init__(
        self,
        renderer: DocumentRendererPort,
        validator: ExportValidator | None = None,
    ) -> None:
        self._renderer = renderer
        self._validator = validator or ExportValidator()

    def execute(
        self,
        document: APADocument,
        semantic_doc: SemanticDocument,
        output_path: Path,
    ) -> ExportResult:
        """Validate and (conditionally) render.

        Args:
            document: The domain-level ``APADocument`` ready to render.
            semantic_doc: The ``SemanticDocument`` used for validation.
            output_path: Desired output file path.

        Returns:
            An ``ExportResult`` with the validation report and,
            if no blocking errors, the rendered file path.
        """
        report = self._validator.validate(semantic_doc)

        if report.is_blocking:
            return ExportResult(report=report, blocked=True)

        # Warnings only or clean — render
        rendered = self._render(document, output_path)
        return ExportResult(report=report, blocked=False, output_path=rendered)

    def force_export(
        self,
        document: APADocument,
        output_path: Path,
    ) -> ExportResult:
        """Bypass validation and render unconditionally.

        Used when the user explicitly acknowledges warnings/errors
        and wants to export anyway.
        """
        rendered = self._render(document, output_path)
        return ExportResult(
            report=ValidationReport(),
            blocked=False,
            output_path=rendered,
        )

    def validate_only(
        self,
        semantic_doc: SemanticDocument,
    ) -> ValidationReport:
        """Run pre-flight checks without rendering.

        Useful for real-time feedback in the GUI before the user
        clicks "Export".
        """
        return self._validator.validate(semantic_doc)

    # -- Internal ------------------------------------------------------------

    def _render(self, document: APADocument, output_path: Path) -> Path:
        """Delegate to the renderer port."""
        try:
            return self._renderer.render(document, output_path)
        except Exception as exc:
            raise DocumentGenerationError(f"Export rendering failed: {exc}") from exc
