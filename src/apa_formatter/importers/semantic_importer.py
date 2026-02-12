"""Semantic document importer — orchestrates the full analysis pipeline.

Wires together:

1. **Parser strategy** (``DocxSemanticParser`` / ``SmartPdfImporter``)
   — file → ``ContentBlock`` list
2. **Handler chain** (Chain of Responsibility) — blocks → builder calls
3. **Builder** (``SemanticDocumentBuilder``) — accumulated state → ``SemanticDocument``
4. *(Optional)* **AI enrichment** (``GeminiEnhancedImporter``) — Gemini-powered
   semantic analysis merged into the builder output

Usage::

    from pathlib import Path
    from apa_formatter.importers.semantic_importer import SemanticImporter

    importer = SemanticImporter()
    result = importer.import_document(Path("paper.docx"))
    # or with AI enrichment
    result = importer.import_document(Path("paper.pdf"), use_ai=True)

    print(result.detected_config.language)    # Language.ES
    print(result.title_page.title)            # "Mi Título"
    print(len(result.references_parsed))      # 12
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from apa_formatter.config.models import PaperSize
from apa_formatter.importers.strategies.docx_semantic import DocxSemanticParser
from apa_formatter.importers.strategies.pdf_semantic import SmartPdfImporter
from apa_formatter.importers.structure_analyzer import (
    AbstractHandler,
    AnalysisContext,
    BodyHandler,
    MetadataHandler,
    ReferenceHandler,
    SemanticDocumentBuilder,
    TitlePageHandler,
)
from apa_formatter.models.semantic_document import (
    SemanticDocument,
    TitlePageData,
)

if TYPE_CHECKING:
    from apa_formatter.infrastructure.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".docx", ".pdf"}


class SemanticImporter:
    """High-level orchestrator for semantic document import.

    Follows a multi-phase pipeline:

    1. **Parse** — convert the raw file into ``ContentBlock`` objects.
    2. **Analyse** — run the Chain of Responsibility handler chain over
       the blocks, populating the builder.
    3. *(Optional)* **AI Enrich** — run ``GeminiEnhancedImporter`` to
       get AI-powered metadata and merge into the builder.
    4. **Build** — materialise the ``SemanticDocument``.

    Parameters
    ----------
    gemini_client:
        Optional pre-configured ``GeminiClient``.  When provided and
        ``use_ai=True``, enables AI enrichment.
    """

    def __init__(self, gemini_client: GeminiClient | None = None) -> None:
        self._gemini_client = gemini_client

    def import_document(
        self,
        path: Path,
        *,
        use_ai: bool = False,
    ) -> SemanticDocument:
        """Import *path* and return a ``SemanticDocument``.

        Parameters
        ----------
        path:
            Path to the DOCX or PDF file.
        use_ai:
            When ``True``, runs Gemini AI enrichment over the
            mechanically-extracted content.  Requires a configured
            ``GeminiClient`` (via constructor or auto-created).

        Supports DOCX and PDF files.  Raises ``ValueError`` for
        unsupported formats or unreadable files.
        """
        suffix = path.suffix.lower()
        if suffix not in _SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Formato no soportado: '{suffix}'. "
                f"Formatos soportados: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}."
            )

        # Phase 1: Parse — choose strategy by extension
        if suffix == ".pdf":
            parser = SmartPdfImporter()
        else:
            parser = DocxSemanticParser()  # type: ignore[assignment]

        blocks = parser.parse(path)

        # Phase 2: Build handler chain
        chain = TitlePageHandler()
        (
            chain.set_next(AbstractHandler())
            .set_next(BodyHandler())
            .set_next(ReferenceHandler())
            .set_next(MetadataHandler())
        )

        # Phase 3: Run chain with builder context
        builder = SemanticDocumentBuilder()
        builder.set_source_path(str(path))
        ctx = AnalysisContext(
            blocks=blocks,
            builder=builder,
            source_path=str(path),
        )
        chain.handle(ctx)

        # Phase 3.5 (optional): AI enrichment
        if use_ai:
            self._apply_ai_enrichment(blocks, builder)

        # Enrich config with parser-level metadata
        config = builder._config
        config.detected_fonts = parser.detected_fonts
        config.line_spacing = parser.dominant_line_spacing

        dims = parser.page_dimensions
        if dims:
            config.page_size = PaperSize(
                nombre="Detectado",
                ancho_cm=dims["width_cm"],
                alto_cm=dims["height_cm"],
            )

        return builder.build()

    # -- AI enrichment -------------------------------------------------------

    def _apply_ai_enrichment(
        self,
        blocks: list,
        builder: SemanticDocumentBuilder,
    ) -> None:
        """Attempt AI enrichment.  Fails silently on errors."""
        client = self._get_or_create_gemini_client()
        if client is None:
            logger.warning(
                "AI enrichment requested but no GeminiClient available. "
                "Falling back to mechanical-only extraction."
            )
            return

        try:
            from apa_formatter.importers.strategies.gemini_strategy import (
                GeminiEnhancedImporter,
            )

            ai_importer = GeminiEnhancedImporter(gemini_client=client)
            ai_result = ai_importer.analyze(blocks)
            self._merge_ai_result(ai_result, builder)
            logger.info("AI enrichment applied successfully.")
        except Exception as exc:
            logger.warning("AI enrichment failed, using mechanical results: %s", exc)

    def _get_or_create_gemini_client(self) -> GeminiClient | None:
        """Return the injected client or try to auto-create one."""
        if self._gemini_client is not None:
            return self._gemini_client

        # Attempt auto-creation (may fail if no key or no SDK)
        try:
            from apa_formatter.infrastructure.ai.gemini_client import (
                GeminiClient as GC,
            )

            self._gemini_client = GC()
            return self._gemini_client
        except Exception as exc:
            logger.debug("Could not auto-create GeminiClient: %s", exc)
            return None

    @staticmethod
    def _merge_ai_result(
        ai_result: object,
        builder: SemanticDocumentBuilder,
    ) -> None:
        """Merge AI-extracted data into the builder.

        AI results *supplement* mechanical extraction — they fill in gaps
        but don't overwrite high-confidence mechanical results.
        """
        from apa_formatter.models.ai_schemas import AiSemanticResult

        if not isinstance(ai_result, AiSemanticResult):
            return

        # Title page: AI wins if mechanical didn't find one, or had low confidence
        if ai_result.title_page:
            mechanical_tp = builder._title_page
            should_replace = (
                mechanical_tp is None or mechanical_tp.confidence < 0.5  # noqa: PLR2004
            )
            if should_replace:
                builder.set_title_page(
                    TitlePageData(
                        title=ai_result.title_page.title,
                        authors=ai_result.title_page.authors or ["Autor desconocido"],
                        affiliation=ai_result.title_page.university,
                        course=ai_result.title_page.course,
                        instructor=ai_result.title_page.instructor,
                        date_text=ai_result.title_page.due_date,
                        confidence=0.9,  # AI-sourced
                    )
                )

        # Abstract: AI wins if mechanical didn't find one
        if ai_result.abstract and builder._abstract is None:
            builder.set_abstract(ai_result.abstract)

        # Keywords: AI wins if mechanical list is empty
        if ai_result.keywords and not builder._keywords:
            builder.set_keywords(ai_result.keywords)

        # References: supplement with AI if mechanical found fewer
        if ai_result.references and not builder._raw_references:
            for ref in ai_result.references:
                builder.add_raw_reference(ref.raw_text)
