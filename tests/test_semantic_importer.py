"""Comprehensive tests for the Semantic Document Analysis System.

Tests cover:
  - ContentBlock dataclass basics
  - SemanticDocumentBuilder (fluent API)
  - Individual handlers (TitlePage, Abstract, Body, Reference, Metadata)
  - Full chain integration
  - SemanticDocument model
  - Edge cases (empty doc, no title page, mixed language)
"""

from __future__ import annotations

import re
from dataclasses import field as dc_field
from unittest.mock import MagicMock, patch

from apa_formatter.domain.models.document import Section
from apa_formatter.domain.models.enums import HeadingLevel, Language
from apa_formatter.domain.models.reference import Author, Reference
from apa_formatter.domain.models.enums import ReferenceType
from apa_formatter.importers.strategies.docx_semantic import ContentBlock
from apa_formatter.importers.structure_analyzer import (
    AbstractHandler,
    AnalysisContext,
    BaseAnalysisHandler,
    BodyHandler,
    MetadataHandler,
    ReferenceHandler,
    SemanticDocumentBuilder,
    TitlePageHandler,
)
from apa_formatter.models.semantic_document import (
    DetectedConfig,
    SemanticDocument,
    TitlePageData,
)
from apa_formatter.config.models import PaperSize


# =========================================================================
# Helpers
# =========================================================================


def _block(
    text: str,
    *,
    style: str = "normal",
    alignment: int | None = None,
    bold: bool = False,
    italic: bool = False,
    font_name: str | None = None,
    font_size: float | None = None,
    page: int = 0,
    heading: int | None = None,
    is_list: bool = False,
) -> ContentBlock:
    """Shorthand factory for test ContentBlocks."""
    return ContentBlock(
        text=text,
        style_name=style,
        alignment=alignment,
        is_bold=bold,
        is_italic=italic,
        font_name=font_name,
        font_size_pt=font_size,
        page_index=page,
        heading_level=heading,
        is_list_item=is_list,
    )


CENTER = 1  # WD_ALIGN_PARAGRAPH.CENTER value


def _make_ctx(blocks: list[ContentBlock]) -> AnalysisContext:
    """Create a fresh AnalysisContext with a builder."""
    return AnalysisContext(
        blocks=blocks,
        builder=SemanticDocumentBuilder(),
    )


# =========================================================================
# 1. ContentBlock Tests
# =========================================================================


class TestContentBlock:
    def test_is_centered(self):
        b = _block("Hello", alignment=CENTER)
        assert b.is_centered

    def test_not_centered(self):
        b = _block("Hello", alignment=0)
        assert not b.is_centered

    def test_is_heading(self):
        b = _block("Intro", heading=1)
        assert b.is_heading

    def test_not_heading(self):
        b = _block("Body text")
        assert not b.is_heading

    def test_is_empty(self):
        b = _block("   ")
        assert b.is_empty

    def test_not_empty(self):
        b = _block("Hello")
        assert not b.is_empty


# =========================================================================
# 2. Builder Tests
# =========================================================================


class TestSemanticDocumentBuilder:
    def test_build_empty(self):
        doc = SemanticDocumentBuilder().build()
        assert doc.title_page is None
        assert doc.abstract is None
        assert doc.body_sections == []
        assert doc.references_raw == []

    def test_set_title_page(self):
        tp = TitlePageData(title="Mi Título", authors=["Juan"])
        doc = SemanticDocumentBuilder().set_title_page(tp).build()
        assert doc.title_page is not None
        assert doc.title_page.title == "Mi Título"
        assert doc.title_page.authors == ["Juan"]

    def test_set_abstract_and_keywords(self):
        doc = (
            SemanticDocumentBuilder()
            .set_abstract("Este es el resumen.")
            .set_keywords(["APA", "formato"])
            .build()
        )
        assert doc.abstract == "Este es el resumen."
        assert doc.keywords == ["APA", "formato"]

    def test_add_sections(self):
        s1 = Section(heading="Intro", level=HeadingLevel.LEVEL_1, content="Texto")
        s2 = Section(heading="Método", level=HeadingLevel.LEVEL_1, content="Datos")
        doc = SemanticDocumentBuilder().add_section(s1).add_section(s2).build()
        assert len(doc.body_sections) == 2
        assert doc.body_sections[0].heading == "Intro"

    def test_add_references(self):
        doc = (
            SemanticDocumentBuilder()
            .add_raw_reference("Smith, J. (2020). Title. Journal.")
            .add_raw_reference("Doe, A. (2019). Book. Publisher.")
            .build()
        )
        assert len(doc.references_raw) == 2

    def test_fluent_chaining(self):
        """Builder methods return self for chaining."""
        builder = SemanticDocumentBuilder()
        result = builder.set_source_path("/tmp/test.docx")
        assert result is builder

    def test_set_config(self):
        cfg = DetectedConfig(language=Language.EN, has_title_page=True)
        doc = SemanticDocumentBuilder().set_config(cfg).build()
        assert doc.detected_config.language == Language.EN
        assert doc.detected_config.has_title_page is True


# =========================================================================
# 3. TitlePageHandler Tests
# =========================================================================


class TestTitlePageHandler:
    def test_detects_centered_bold_title_page(self):
        blocks = [
            _block("Mi Gran Título de Investigación", alignment=CENTER, bold=True, page=0),
            _block("Juan Pérez", alignment=CENTER, page=0),
            _block("María López", alignment=CENTER, page=0),
            _block("Universidad Nacional de Colombia", alignment=CENTER, page=0),
            _block("2024", alignment=CENTER, page=0),
        ]
        ctx = _make_ctx(blocks)
        TitlePageHandler()._process(ctx)
        tp = ctx.builder._title_page
        assert tp is not None
        assert tp.title == "Mi Gran Título de Investigación"
        assert "Juan Pérez" in tp.authors
        assert tp.affiliation is not None
        assert "Universidad" in tp.affiliation

    def test_no_title_page_if_not_centered(self):
        blocks = [
            _block("Introduction", bold=True, page=0),
            _block("Body paragraph text goes here.", page=0),
        ]
        ctx = _make_ctx(blocks)
        TitlePageHandler()._process(ctx)
        assert ctx.builder._title_page is None

    def test_institution_keyword_triggers_detection(self):
        """Even without heavy centring, institution keywords help."""
        blocks = [
            _block("My Research Paper", alignment=CENTER, bold=True, page=0),
            _block("John Doe", alignment=CENTER, page=0),
            _block("Faculty of Science", alignment=CENTER, page=0),
        ]
        ctx = _make_ctx(blocks)
        TitlePageHandler()._process(ctx)
        assert ctx.builder._title_page is not None

    def test_date_extraction(self):
        blocks = [
            _block("Título", alignment=CENTER, bold=True, page=0),
            _block("Autor", alignment=CENTER, page=0),
            _block("Universidad X", alignment=CENTER, page=0),
            _block("12 de marzo de 2024", alignment=CENTER, page=0),
        ]
        ctx = _make_ctx(blocks)
        TitlePageHandler()._process(ctx)
        tp = ctx.builder._title_page
        assert tp is not None
        assert tp.date_text is not None
        assert "2024" in tp.date_text

    def test_marks_first_page_consumed(self):
        blocks = [
            _block("Title", alignment=CENTER, bold=True, page=0),
            _block("Author", alignment=CENTER, page=0),
            _block("Universidad X", alignment=CENTER, page=0),
            _block("Body text on page 2", page=1),
        ]
        ctx = _make_ctx(blocks)
        TitlePageHandler()._process(ctx)
        # First 3 blocks (page 0) should be consumed
        assert 0 in ctx.consumed_indices
        assert 1 in ctx.consumed_indices
        assert 2 in ctx.consumed_indices
        # Page 2 block NOT consumed
        assert 3 not in ctx.consumed_indices


# =========================================================================
# 4. AbstractHandler Tests
# =========================================================================


class TestAbstractHandler:
    def test_detects_abstract_section(self):
        blocks = [
            _block("Resumen", bold=True, heading=1),
            _block("Este estudio examina el efecto de las normas APA."),
            _block("Los resultados fueron significativos."),
            _block("Introducción", bold=True, heading=1),
        ]
        ctx = _make_ctx(blocks)
        AbstractHandler()._process(ctx)
        assert ctx.builder._abstract is not None
        assert "efecto" in ctx.builder._abstract

    def test_detects_english_abstract(self):
        blocks = [
            _block("Abstract", bold=True, heading=1),
            _block("This study analyses the effects of APA formatting."),
            _block("Method", bold=True, heading=1),
        ]
        ctx = _make_ctx(blocks)
        AbstractHandler()._process(ctx)
        assert ctx.builder._abstract is not None
        assert "APA" in ctx.builder._abstract

    def test_extracts_keywords(self):
        blocks = [
            _block("Resumen", bold=True, heading=1),
            _block("Este es el resumen del documento."),
            _block("Palabras clave: APA, formato, referencias"),
            _block("Introducción", bold=True, heading=1),
        ]
        ctx = _make_ctx(blocks)
        AbstractHandler()._process(ctx)
        assert ctx.builder._keywords == ["APA", "formato", "referencias"]

    def test_no_abstract_when_missing(self):
        blocks = [
            _block("Introducción", bold=True, heading=1),
            _block("Body text here."),
        ]
        ctx = _make_ctx(blocks)
        AbstractHandler()._process(ctx)
        assert ctx.builder._abstract is None

    def test_skips_consumed_blocks(self):
        blocks = [
            _block("Resumen", bold=True, heading=1),
            _block("Already consumed content."),
        ]
        ctx = _make_ctx(blocks)
        ctx.consumed_indices.add(0)
        ctx.consumed_indices.add(1)
        AbstractHandler()._process(ctx)
        assert ctx.builder._abstract is None


# =========================================================================
# 5. BodyHandler Tests
# =========================================================================


class TestBodyHandler:
    def test_maps_headings_to_sections(self):
        blocks = [
            _block("Introducción", heading=1),
            _block("Párrafo introductorio."),
            _block("Método", heading=2),
            _block("Descripción del método."),
        ]
        ctx = _make_ctx(blocks)
        BodyHandler()._process(ctx)
        sections = ctx.builder._sections
        assert len(sections) == 2
        assert sections[0].heading == "Introducción"
        assert sections[0].level == HeadingLevel.LEVEL_1
        assert sections[1].heading == "Método"
        assert sections[1].level == HeadingLevel.LEVEL_2

    def test_stops_at_references_heading(self):
        blocks = [
            _block("Introducción", heading=1),
            _block("Text."),
            _block("Referencias", bold=True, heading=1),
            _block("Smith (2020). Title."),
        ]
        ctx = _make_ctx(blocks)
        BodyHandler()._process(ctx)
        sections = ctx.builder._sections
        assert len(sections) == 1
        assert sections[0].heading == "Introducción"

    def test_handles_list_items(self):
        blocks = [
            _block("Método", heading=1),
            _block("Paso 1", is_list=True),
            _block("Paso 2", is_list=True),
        ]
        ctx = _make_ctx(blocks)
        BodyHandler()._process(ctx)
        content = ctx.builder._sections[0].content
        assert "- Paso 1" in content
        assert "- Paso 2" in content

    def test_body_without_headings(self):
        blocks = [
            _block("Just a paragraph of text."),
            _block("Another paragraph."),
        ]
        ctx = _make_ctx(blocks)
        BodyHandler()._process(ctx)
        sections = ctx.builder._sections
        assert len(sections) == 1
        assert sections[0].heading is None

    def test_skips_consumed_blocks(self):
        blocks = [
            _block("Consumed heading", heading=1),
            _block("Body text."),
        ]
        ctx = _make_ctx(blocks)
        ctx.consumed_indices = {0, 1}
        BodyHandler()._process(ctx)
        assert ctx.builder._sections == []


# =========================================================================
# 6. ReferenceHandler Tests
# =========================================================================


class TestReferenceHandler:
    def test_collects_raw_references(self):
        blocks = [
            _block("Body text."),
            _block("Referencias", bold=True, heading=1),
            _block("Smith, J. (2020). Title. Journal, 1(2), 3-4."),
            _block("Doe, A. (2019). Book title. Publisher."),
        ]
        ctx = _make_ctx(blocks)
        ReferenceHandler()._process(ctx)
        assert len(ctx.builder._raw_references) == 2
        assert "Smith" in ctx.builder._raw_references[0]

    def test_detects_english_references_heading(self):
        blocks = [
            _block("References", bold=True, heading=1),
            _block("Entry 1."),
        ]
        ctx = _make_ctx(blocks)
        ReferenceHandler()._process(ctx)
        assert len(ctx.builder._raw_references) == 1

    def test_no_references_section(self):
        blocks = [
            _block("Introducción", heading=1),
            _block("Just body text."),
        ]
        ctx = _make_ctx(blocks)
        ReferenceHandler()._process(ctx)
        assert ctx.builder._raw_references == []

    def test_marks_reference_blocks_consumed(self):
        blocks = [
            _block("References", bold=True, heading=1),
            _block("Ref 1."),
            _block("Ref 2."),
        ]
        ctx = _make_ctx(blocks)
        ReferenceHandler()._process(ctx)
        assert 0 in ctx.consumed_indices
        assert 1 in ctx.consumed_indices
        assert 2 in ctx.consumed_indices


# =========================================================================
# 7. MetadataHandler Tests
# =========================================================================


class TestMetadataHandler:
    def test_detects_spanish(self):
        blocks = [
            _block("El estudio de las normas APA en la universidad."),
            _block("Los resultados de la investigación son significativos."),
            _block("Se analizaron los datos con un enfoque cualitativo."),
        ]
        ctx = _make_ctx(blocks)
        MetadataHandler()._process(ctx)
        assert ctx.builder._config.language == Language.ES

    def test_detects_english(self):
        blocks = [
            _block("The study of APA formatting in the university."),
            _block("The results of the research are significant."),
            _block("The data was analysed with a qualitative approach."),
        ]
        ctx = _make_ctx(blocks)
        MetadataHandler()._process(ctx)
        assert ctx.builder._config.language == Language.EN

    def test_updates_has_title_page_flag(self):
        blocks = [_block("Text")]
        ctx = _make_ctx(blocks)
        ctx.builder.set_title_page(TitlePageData(title="T", authors=["A"]))
        MetadataHandler()._process(ctx)
        assert ctx.builder._config.has_title_page is True

    def test_updates_has_abstract_flag(self):
        blocks = [_block("Text")]
        ctx = _make_ctx(blocks)
        ctx.builder.set_abstract("Resumen del documento.")
        MetadataHandler()._process(ctx)
        assert ctx.builder._config.has_abstract is True


# =========================================================================
# 8. Chain Integration Tests
# =========================================================================


class TestChainIntegration:
    def _run_chain(self, blocks: list[ContentBlock]) -> SemanticDocument:
        chain = TitlePageHandler()
        (
            chain.set_next(AbstractHandler())
            .set_next(BodyHandler())
            .set_next(ReferenceHandler())
            .set_next(MetadataHandler())
        )
        builder = SemanticDocumentBuilder()
        ctx = AnalysisContext(blocks=blocks, builder=builder)
        chain.handle(ctx)
        return builder.build()

    def test_full_document_analysis(self):
        """Simulates a complete academic paper in Spanish."""
        blocks = [
            # Title page
            _block("Análisis de Normas APA", alignment=CENTER, bold=True, page=0),
            _block("Carlos García", alignment=CENTER, page=0),
            _block("Universidad de los Andes", alignment=CENTER, page=0),
            _block("2024", alignment=CENTER, page=0),
            # Abstract
            _block("Resumen", bold=True, heading=1, page=1),
            _block("Este estudio analiza el uso de las normas APA.", page=1),
            _block("Palabras clave: APA, formato, escritura académica", page=1),
            # Body
            _block("Introducción", heading=1, page=2),
            _block("Las normas APA son un estándar en la escritura académica.", page=2),
            _block("Método", heading=2, page=3),
            _block("Se utilizó un enfoque mixto para el análisis.", page=3),
            # References
            _block("Referencias", bold=True, heading=1, page=4),
            _block("García, C. (2020). Título del artículo. Revista, 1(2), 3.", page=4),
            _block("López, M. (2019). Otro título. Editorial.", page=4),
        ]
        doc = self._run_chain(blocks)

        # Title page
        assert doc.title_page is not None
        assert "Análisis" in doc.title_page.title
        assert "Carlos García" in doc.title_page.authors
        assert "Universidad" in (doc.title_page.affiliation or "")

        # Abstract
        assert doc.abstract is not None
        assert "normas APA" in doc.abstract

        # Keywords
        assert "APA" in doc.keywords

        # Body sections
        assert len(doc.body_sections) == 2
        assert doc.body_sections[0].heading == "Introducción"
        assert doc.body_sections[1].heading == "Método"

        # References
        assert len(doc.references_raw) == 2

        # Config
        assert doc.detected_config.language == Language.ES
        assert doc.detected_config.has_title_page is True
        assert doc.detected_config.has_abstract is True

    def test_document_without_title_page(self):
        blocks = [
            _block("Introduction", heading=1, page=0),
            _block("This paper discusses APA formatting.", page=0),
            _block("References", bold=True, heading=1, page=1),
            _block("Smith (2020). Title. Journal.", page=1),
        ]
        doc = self._run_chain(blocks)
        assert doc.title_page is None
        assert len(doc.body_sections) == 1
        assert len(doc.references_raw) == 1

    def test_empty_document(self):
        doc = self._run_chain([])
        assert doc.title_page is None
        assert doc.abstract is None
        assert doc.body_sections == []
        assert doc.references_raw == []

    def test_handler_chain_order(self):
        """Verify that set_next returns the next handler for chaining."""
        h1 = TitlePageHandler()
        h2 = AbstractHandler()
        h3 = BodyHandler()
        result = h1.set_next(h2)
        assert result is h2
        result2 = h2.set_next(h3)
        assert result2 is h3


# =========================================================================
# 9. SemanticDocument Model Tests
# =========================================================================


class TestSemanticDocumentModel:
    def test_default_values(self):
        doc = SemanticDocument()
        assert doc.title_page is None
        assert doc.abstract is None
        assert doc.keywords == []
        assert doc.body_sections == []
        assert doc.references_raw == []
        assert doc.references_parsed == []
        assert doc.source_path == ""

    def test_detected_config_defaults(self):
        cfg = DetectedConfig()
        assert cfg.language == Language.ES
        assert cfg.page_size is None
        assert cfg.has_title_page is False
        assert cfg.detected_fonts == []

    def test_title_page_data_defaults(self):
        tp = TitlePageData()
        assert tp.title == "Documento sin título"
        assert tp.authors == ["Autor desconocido"]
        assert tp.confidence == 0.0

    def test_title_page_confidence_bounds(self):
        tp = TitlePageData(confidence=0.85)
        assert 0.0 <= tp.confidence <= 1.0
