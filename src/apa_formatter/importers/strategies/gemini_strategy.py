"""Gemini-enhanced semantic import strategy.

Implements a hybrid import pipeline that combines mechanical text extraction
(via ``DocxSemanticParser`` / ``SmartPdfImporter``) with AI-powered semantic
comprehension using Google Gemini.

The strategy:

1. **Mechanical extraction** — get ``ContentBlock`` list from existing parsers.
2. **Smart chunking** — select strategically important text fragments:
   - *Front chunk* (pages 0–1): title page + abstract
   - *Back chunk* (last 3 pages): references
   - *TOC chunk* (if detected): document structure
3. **AI analysis** — send each chunk to Gemini with specialised prompts.
4. **Merge** — enrich the builder with AI-extracted metadata.

Usage::

    from apa_formatter.importers.strategies.gemini_strategy import (
        GeminiEnhancedImporter,
    )

    importer = GeminiEnhancedImporter(gemini_client=client)
    ai_result = importer.analyze(blocks)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apa_formatter.importers.strategies.docx_semantic import ContentBlock
from apa_formatter.models.ai_schemas import AiSemanticResult

if TYPE_CHECKING:
    from apa_formatter.infrastructure.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_FRONT = """\
Eres un experto editor APA 7ª edición. Tu trabajo es analizar el texto crudo \
extraído de las primeras páginas de un documento académico e identificar \
metadatos estructurados.

Reglas:
- Ignora números de página y encabezados/pies de página repetitivos.
- Identifica la PORTADA: título del documento, lista de autores, \
universidad/institución, curso/asignatura, instructor/profesor, y fecha.
- Identifica el ABSTRACT/RESUMEN y sus PALABRAS CLAVE si están presentes.
- Si detectas secciones iniciales (Introducción, etc.), inclúyelas con su \
nivel de encabezado (1-5).
- Devuelve JSON estricto según el esquema proporcionado.
- Si un campo no se puede determinar, déjalo como null o lista vacía.
"""

_SYSTEM_PROMPT_BACK = """\
Eres un experto editor APA 7ª edición. Tu trabajo es analizar el texto crudo \
extraído de las últimas páginas de un documento académico para identificar \
las REFERENCIAS BIBLIOGRÁFICAS.

Reglas:
- Ignora números de página y encabezados/pies de página repetitivos.
- Cada entrada de referencia es un párrafo separado que comienza con un \
apellido de autor.
- Para cada referencia, extrae: texto completo, autores, año, título y fuente.
- No inventes referencias. Solo extrae las que están presentes en el texto.
- Devuelve JSON estricto según el esquema proporcionado.
"""

_SYSTEM_PROMPT_TOC = """\
Eres un experto editor APA 7ª edición. Tu trabajo es analizar la tabla de \
contenidos (índice) de un documento académico para entender su estructura.

Reglas:
- Identifica cada sección con su nivel de encabezado (1-5).
- El nivel se infiere por la indentación o numeración.
- Devuelve JSON estricto según el esquema proporcionado.
- Solo incluye secciones en el campo "sections", deja los demás campos vacíos.
"""

# TOC heading patterns
_TOC_HEADINGS = {
    "contenido",
    "tabla de contenido",
    "table of contents",
    "contents",
    "índice",
    "indice",
}


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------


class GeminiEnhancedImporter:
    """Hybrid importer that enriches mechanical extraction with Gemini AI.

    Parameters
    ----------
    gemini_client:
        Configured ``GeminiClient`` instance.
    front_pages:
        Number of leading pages to send for title/abstract analysis.
    back_pages:
        Number of trailing pages to send for reference analysis.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        *,
        front_pages: int = 2,
        back_pages: int = 3,
    ) -> None:
        self._client = gemini_client
        self._front_pages = front_pages
        self._back_pages = back_pages

    # -- Public API ----------------------------------------------------------

    def analyze(self, blocks: list[ContentBlock]) -> AiSemanticResult:
        """Run AI analysis on strategically-chunked portions of *blocks*.

        Returns an ``AiSemanticResult`` with all fields populated by AI.
        Individual chunk failures are logged but do not abort the analysis;
        partial results are returned.
        """
        result = AiSemanticResult()

        if not blocks:
            return result

        # --- Front chunk (title page + abstract) ---------------------------
        front_text = self._extract_front_chunk(blocks)
        if front_text:
            try:
                front_result = self._client.analyze_text(
                    text=front_text,
                    schema=AiSemanticResult,
                    system_prompt=_SYSTEM_PROMPT_FRONT,
                )
                front_parsed = AiSemanticResult.model_validate(front_result)
                result.title_page = front_parsed.title_page
                result.abstract = front_parsed.abstract
                result.keywords = front_parsed.keywords
                # Keep early sections if detected
                if front_parsed.sections:
                    result.sections.extend(front_parsed.sections)
            except Exception as exc:
                logger.warning("AI front-chunk analysis failed: %s", exc)

        # --- Back chunk (references) ---------------------------------------
        back_text = self._extract_back_chunk(blocks)
        if back_text:
            try:
                back_result = self._client.analyze_text(
                    text=back_text,
                    schema=AiSemanticResult,
                    system_prompt=_SYSTEM_PROMPT_BACK,
                )
                back_parsed = AiSemanticResult.model_validate(back_result)
                result.references = back_parsed.references
            except Exception as exc:
                logger.warning("AI back-chunk analysis failed: %s", exc)

        # --- TOC chunk (structure) -----------------------------------------
        toc_text = self._extract_toc_chunk(blocks)
        if toc_text:
            try:
                toc_result = self._client.analyze_text(
                    text=toc_text,
                    schema=AiSemanticResult,
                    system_prompt=_SYSTEM_PROMPT_TOC,
                )
                toc_parsed = AiSemanticResult.model_validate(toc_result)
                if toc_parsed.sections:
                    # TOC sections replace any previously detected sections
                    result.sections = toc_parsed.sections
            except Exception as exc:
                logger.warning("AI TOC-chunk analysis failed: %s", exc)

        return result

    # -- Chunking helpers ----------------------------------------------------

    def _extract_front_chunk(self, blocks: list[ContentBlock]) -> str:
        """Extract text from the first *front_pages* pages."""
        lines: list[str] = []
        for block in blocks:
            if block.page_index >= self._front_pages:
                break
            text = block.text.strip()
            if text:
                lines.append(text)
        return "\n".join(lines)

    def _extract_back_chunk(self, blocks: list[ContentBlock]) -> str:
        """Extract text from the last *back_pages* pages."""
        if not blocks:
            return ""

        max_page = max(b.page_index for b in blocks)
        cutoff_page = max(0, max_page - self._back_pages + 1)

        lines: list[str] = []
        for block in blocks:
            if block.page_index >= cutoff_page:
                text = block.text.strip()
                if text:
                    lines.append(text)
        return "\n".join(lines)

    def _extract_toc_chunk(self, blocks: list[ContentBlock]) -> str:
        """Extract text from a detected Table of Contents section.

        Returns empty string if no TOC heading is found.
        """
        toc_start: int | None = None

        for i, block in enumerate(blocks):
            text_lower = block.text.strip().lower()
            if text_lower in _TOC_HEADINGS:
                toc_start = i
                break

        if toc_start is None:
            return ""

        # Collect until next heading-level block or page change
        toc_page = blocks[toc_start].page_index
        lines: list[str] = []
        for block in blocks[toc_start:]:
            # Stop if we moved more than 2 pages past the TOC heading
            if block.page_index > toc_page + 2:
                break
            text = block.text.strip()
            if text:
                lines.append(text)

        return "\n".join(lines)

    @staticmethod
    def blocks_to_text(blocks: list[ContentBlock]) -> str:
        """Convert a list of content blocks to a plain-text string."""
        return "\n".join(b.text.strip() for b in blocks if b.text.strip())
