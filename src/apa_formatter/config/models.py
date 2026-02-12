"""Pydantic models for APA 7 configuration.

These models validate and type the JSON configuration file that drives
all formatting rules for the APA 7 document generator.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


class MetaData(BaseModel):
    """Metadata about the APA standard being used."""

    norma: str = "APA"
    edicion: str = "7ma"
    idioma: str = "Español"
    descripcion: str = "Reglas extraídas de la Guía Normas APA 7ma edición"
    fuente_origen: str = "Guia-Normas-APA-7ma-edicion.pdf"


# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------


class PaperSize(BaseModel):
    """Paper dimensions."""

    nombre: str = "Carta"
    ancho_cm: float = 21.59
    alto_cm: float = 27.94
    nota: Optional[str] = "Equivalente a 8 1/2 x 11 pulgadas"

    @property
    def ancho_inches(self) -> float:
        return self.ancho_cm / 2.54

    @property
    def alto_inches(self) -> float:
        return self.alto_cm / 2.54


class BindingMargins(BaseModel):
    """Binding margin override (used when document needs binding)."""

    descripcion: str = "Cuando se requiera empastar el trabajo"
    izquierda_cm: float = 4.0
    nota: Optional[str] = None

    @property
    def izquierda_inches(self) -> float:
        return self.izquierda_cm / 2.54


class Margins(BaseModel):
    """Page margins in centimeters."""

    superior_cm: float = 2.54
    inferior_cm: float = 2.54
    izquierda_cm: float = 2.54
    derecha_cm: float = 2.54
    nota: Optional[str] = "1 pulgada en todos los lados"
    condicion_empaste: Optional[BindingMargins] = None

    @property
    def superior_inches(self) -> float:
        return self.superior_cm / 2.54

    @property
    def inferior_inches(self) -> float:
        return self.inferior_cm / 2.54

    @property
    def izquierda_inches(self) -> float:
        return self.izquierda_cm / 2.54

    @property
    def derecha_inches(self) -> float:
        return self.derecha_cm / 2.54


class Pagination(BaseModel):
    """Page number configuration."""

    ubicacion: str = "esquina_superior_derecha"
    inicio: str = "portada_numero_1"
    formato: str = "numeros_arabigos"


class PageConfig(BaseModel):
    """Complete page configuration."""

    tamaño_papel: PaperSize = Field(default_factory=PaperSize)
    margenes: Margins = Field(default_factory=Margins)
    paginacion: Pagination = Field(default_factory=Pagination)


# ---------------------------------------------------------------------------
# Fonts & Typography
# ---------------------------------------------------------------------------


class TableContentFont(BaseModel):
    """Font specification for table content (institutional overrides)."""

    tamaño_pt: int = 10
    tipo: str = "Misma fuente que el documento"


class TableVisualFormat(BaseModel):
    """Visual formatting rules for tables."""

    lineas_horizontales: int = 3
    lineas_verticales: bool = False
    descripcion: Optional[str] = "Solo línea superior, inferior y separador de cabecera"


class FontConfig(BaseModel):
    """A single accepted font specification."""

    tipo: str = Field(..., description="sans_serif or serif")
    nombre: str = Field(..., description="Font family name")
    tamaño_pt: int = Field(..., description="Font size in points")
    nota: Optional[str] = Field(None, description="Optional note about the font")


class FontExceptionFigures(BaseModel):
    """Font exceptions for figures."""

    tipo: str = "sans_serif"
    tamaño_min_pt: int = 8
    tamaño_max_pt: int = 14


class FontExceptionCode(BaseModel):
    """Font exceptions for source code."""

    fuentes: list[str] = Field(default_factory=lambda: ["Lucida Console", "Courier New"])
    tamaño_pt: int = 10
    tipo: str = "monoespaciada"


class FontExceptionFootnotes(BaseModel):
    """Font exceptions for footnotes."""

    tamaño: str = "menor_al_texto"
    interlineado: str = "sencillo"


class FontExceptions(BaseModel):
    """Font exceptions for specific contexts."""

    figuras: FontExceptionFigures = Field(default_factory=FontExceptionFigures)
    codigo_fuente: FontExceptionCode = Field(default_factory=FontExceptionCode)
    notas_al_pie: FontExceptionFootnotes = Field(default_factory=FontExceptionFootnotes)


class TypographyConfig(BaseModel):
    """Complete fonts and typography configuration."""

    fuentes_aceptadas: list[FontConfig] = Field(
        default_factory=lambda: [
            FontConfig(tipo="sans_serif", nombre="Calibri", tamaño_pt=11),
            FontConfig(tipo="sans_serif", nombre="Arial", tamaño_pt=11),
            FontConfig(tipo="sans_serif", nombre="Lucida Sans Unicode", tamaño_pt=10),
            FontConfig(tipo="serif", nombre="Times New Roman", tamaño_pt=12),
            FontConfig(tipo="serif", nombre="Georgia", tamaño_pt=11),
            FontConfig(tipo="serif", nombre="Computer Modern", tamaño_pt=10),
        ]
    )
    excepciones: FontExceptions = Field(default_factory=FontExceptions)


# ---------------------------------------------------------------------------
# Text Formatting
# ---------------------------------------------------------------------------


class ParagraphIndent(BaseModel):
    """Paragraph indent configuration."""

    medida_cm: float = 1.27
    tipo: str = "primera_linea"
    nota: Optional[str] = "Equivalente a 1/2 pulgada"

    @property
    def medida_inches(self) -> float:
        return self.medida_cm / 2.54


class ParagraphSpacing(BaseModel):
    """Paragraph spacing configuration."""

    anterior_pt: int = 0
    posterior_pt: int = 0
    nota: Optional[str] = "No agregar espacio extra entre párrafos"


class TextFormatConfig(BaseModel):
    """Text formatting configuration."""

    alineacion: str = "izquierda"
    justificado: bool = False
    interlineado_general: float = 2.0
    sangria_parrafo: ParagraphIndent = Field(default_factory=ParagraphIndent)
    espaciado_parrafos: ParagraphSpacing = Field(default_factory=ParagraphSpacing)


# ---------------------------------------------------------------------------
# Heading Hierarchy
# ---------------------------------------------------------------------------


class HeadingFormat(BaseModel):
    """Format details for a heading level."""

    alineacion: str = "izquierda"
    negrita: bool = True
    cursiva: bool = False
    punto_final: bool = False
    sangria_cm: Optional[float] = None

    @property
    def sangria_inches(self) -> float:
        return (self.sangria_cm or 0) / 2.54


class HeadingConfig(BaseModel):
    """Style rules for a single heading level."""

    nivel: int = Field(..., ge=1, le=5)
    formato: HeadingFormat = Field(default_factory=HeadingFormat)
    inicio_texto: str = "nuevo_parrafo"

    # ----- Convenience properties (delegate to formato) -----

    @property
    def is_centered(self) -> bool:
        return self.formato.alineacion == "centrado"

    @property
    def is_bold(self) -> bool:
        return self.formato.negrita

    @property
    def is_italic(self) -> bool:
        return self.formato.cursiva

    @property
    def is_inline(self) -> bool:
        return self.inicio_texto == "misma_linea"

    @property
    def is_indented(self) -> bool:
        return (self.formato.sangria_cm or 0) > 0

    @property
    def sangria_inches(self) -> float:
        return self.formato.sangria_inches


# ---------------------------------------------------------------------------
# Document Elements
# ---------------------------------------------------------------------------


class KeywordsConfig(BaseModel):
    """Keywords section configuration."""

    etiqueta: str = "Palabras clave:"
    formato_etiqueta: str = "cursiva"
    sangria: bool = True


class AbstractConfig(BaseModel):
    """Abstract section configuration."""

    titulo: str = "Resumen"
    formato_titulo: str = "centrado_negrita"
    limite_palabras_min: int = 150
    limite_palabras_max: int = 250
    sangria_primera_linea: bool = False
    palabras_clave: KeywordsConfig = Field(default_factory=KeywordsConfig)


class CoverPageConfig(BaseModel):
    """Cover page elements for each document variant."""

    estudiante: list[str] = Field(
        default_factory=lambda: [
            "numero_pagina",
            "titulo_trabajo",
            "autores",
            "afiliacion_universidad",
            "nombre_curso",
            "instructor",
            "fecha",
        ]
    )
    profesional: list[str] = Field(
        default_factory=lambda: [
            "numero_pagina",
            "titulo_corto_header",
            "titulo_trabajo",
            "autores",
            "afiliacion",
            "nota_autor",
        ]
    )


class DocumentElements(BaseModel):
    """Document structure and elements configuration."""

    orden_secciones: list[str] = Field(
        default_factory=lambda: [
            "portada",
            "resumen",
            "texto",
            "referencias",
            "notas",
            "tablas",
            "figuras",
            "apendice",
        ]
    )
    portada: CoverPageConfig = Field(default_factory=CoverPageConfig)
    resumen: AbstractConfig = Field(default_factory=AbstractConfig)


# ---------------------------------------------------------------------------
# Citation Rules
# ---------------------------------------------------------------------------


class CitationGeneralRules(BaseModel):
    """General citation system rules."""

    sistema: str = "autor-fecha"
    fuentes_secundarias_texto: str = "como se citó en"


class ShortQuoteRules(BaseModel):
    """Rules for short in-text quotations (<40 words)."""

    max_palabras: int = 39
    formato: str = "entre_comillas"
    ubicacion: str = "integrada_en_texto"
    requiere: list[str] = Field(default_factory=lambda: ["apellido", "año", "pagina"])


class BlockQuoteRules(BaseModel):
    """Rules for block quotations (≥40 words)."""

    min_palabras: int = 40
    formato: str = "bloque_aparte"
    comillas: bool = False
    sangria_bloque_cm: float = 1.27
    sangria_parrafos_adicionales_cm: float = 1.27
    interlineado: float = 2.0
    ubicacion_punto: str = "antes_del_parentesis"

    @property
    def sangria_bloque_inches(self) -> float:
        return self.sangria_bloque_cm / 2.54


class ParaphrasingRules(BaseModel):
    """Rules for paraphrasing."""

    requiere: list[str] = Field(default_factory=lambda: ["apellido", "año"])
    recomendado: list[str] = Field(default_factory=lambda: ["pagina_o_parrafo"])


class AuthorCitationPatterns(BaseModel):
    """Author formatting patterns for in-text citations."""

    un_autor: str = "Apellido (Año)"
    dos_autores: str = "Apellido1 y Apellido2 (Año)"
    tres_o_mas_autores: str = "Apellido1 et al. (Año)"
    corporativo_primera_vez: str = "Nombre Completo [Siglas] (Año)"
    corporativo_siguientes: str = "Siglas (Año)"


class CitationRules(BaseModel):
    """Complete citation rules."""

    reglas_generales: CitationGeneralRules = Field(default_factory=CitationGeneralRules)
    cita_textual_corta: ShortQuoteRules = Field(default_factory=ShortQuoteRules)
    cita_textual_bloque: BlockQuoteRules = Field(default_factory=BlockQuoteRules)
    parafraseo: ParaphrasingRules = Field(default_factory=ParaphrasingRules)
    autores: AuthorCitationPatterns = Field(default_factory=AuthorCitationPatterns)


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


class ReferenceFormatConfig(BaseModel):
    """Reference list formatting rules."""

    titulo: str = "Referencias"
    alineacion_titulo: str = "centrado_negrita"
    orden: str = "alfabetico_autor"
    sangria_francesa_cm: float = 1.27
    interlineado: float = 2.0

    @property
    def sangria_francesa_inches(self) -> float:
        return self.sangria_francesa_cm / 2.54


class AuthorLimits(BaseModel):
    """Author display limits in reference list."""

    hasta: int = 20
    regla_mas_de_20: str = "listar_primeros_19_y_ultimo"


class SpecialCases(BaseModel):
    """Reference special cases."""

    sin_fecha: str = "s.f."
    doi_url: str = "sin_saltos_manuales"


class ReferenceConfig(BaseModel):
    """Complete reference section configuration."""

    formato_lista: ReferenceFormatConfig = Field(default_factory=ReferenceFormatConfig)
    limite_autores_mostrar: AuthorLimits = Field(default_factory=AuthorLimits)
    elementos_basicos: list[str] = Field(
        default_factory=lambda: ["autor", "fecha", "titulo", "fuente"]
    )
    casos_especiales: SpecialCases = Field(default_factory=SpecialCases)


# ---------------------------------------------------------------------------
# Tables & Figures
# ---------------------------------------------------------------------------


class NumberingStyle(BaseModel):
    """Numbering style for tables/figures."""

    estilo: str = "negrita"
    ejemplo: str = "Tabla 1"


class TitleStyle(BaseModel):
    """Title style for tables/figures."""

    ubicacion: str = "debajo_numero"
    estilo: str = "cursiva"
    interlineado: float = 2.0


class TableBorders(BaseModel):
    """Table border configuration."""

    bordes: str = "solo_horizontales_principales"
    bordes_verticales: bool = False


class TableFigureNotes(BaseModel):
    """Notes configuration for tables/figures."""

    prefijo: str = "Nota."
    estilo_prefijo: str = "cursiva"
    contenido: str = "derechos_autor_explicaciones"


class TablesAndFiguresConfig(BaseModel):
    """Complete tables and figures configuration."""

    numeracion: NumberingStyle = Field(default_factory=NumberingStyle)
    titulo: TitleStyle = Field(default_factory=TitleStyle)
    tablas: TableBorders = Field(default_factory=TableBorders)
    notas: TableFigureNotes = Field(default_factory=TableFigureNotes)
    fuente_contenido: Optional[TableContentFont] = None
    formato_visual: Optional[TableVisualFormat] = None


# ---------------------------------------------------------------------------
# Institutional Metadata
# ---------------------------------------------------------------------------


class InstitutionalMetadata(BaseModel):
    """Metadata for an institutional config profile (e.g. SENA)."""

    institucion: str
    base: str = "APA 7ma Edición"
    fuente_documento: Optional[str] = None
    año_documento: Optional[int] = None


# ---------------------------------------------------------------------------
# Colombian Legal References
# ---------------------------------------------------------------------------


class LegalReferenceTemplate(BaseModel):
    """A legal reference template with pattern and example."""

    plantilla: str
    ejemplo: str


class AdministrativeActTemplate(BaseModel):
    """Template for administrative acts (Decretos, Acuerdos, etc.)."""

    tipos: list[str] = Field(
        default_factory=lambda: [
            "Decreto",
            "Ordenanza",
            "Acuerdo",
            "Resolución",
        ]
    )
    plantilla: str = "{Tipo} {Numero} de {Año} [{EntePromulgador}]. {Asunto}. {FechaPromulgacion}."
    ejemplo: str = ""


class ColombianLegalReferences(BaseModel):
    """Colombian legal reference formats adapted from Bluebook for SENA."""

    descripcion: str = "Adaptación del Bluebook para el contexto legal colombiano"
    formatos_plantilla: dict[str, LegalReferenceTemplate | AdministrativeActTemplate] = Field(
        default_factory=dict
    )


# ---------------------------------------------------------------------------
# Root Config
# ---------------------------------------------------------------------------


class APAConfig(BaseModel):
    """Root configuration model — the single source of truth for all APA 7 rules."""

    metadata: MetaData = Field(default_factory=MetaData)
    configuracion_pagina: PageConfig = Field(default_factory=PageConfig)
    fuentes_y_tipografia: TypographyConfig = Field(default_factory=TypographyConfig)
    formato_texto: TextFormatConfig = Field(default_factory=TextFormatConfig)
    jerarquia_titulos: list[HeadingConfig] = Field(
        default_factory=lambda: [
            HeadingConfig(
                nivel=1,
                formato=HeadingFormat(alineacion="centrado", negrita=True),
                inicio_texto="nuevo_parrafo",
            ),
            HeadingConfig(
                nivel=2,
                formato=HeadingFormat(alineacion="izquierda", negrita=True),
                inicio_texto="nuevo_parrafo",
            ),
            HeadingConfig(
                nivel=3,
                formato=HeadingFormat(alineacion="izquierda", negrita=True, cursiva=True),
                inicio_texto="nuevo_parrafo",
            ),
            HeadingConfig(
                nivel=4,
                formato=HeadingFormat(
                    alineacion="izquierda",
                    sangria_cm=1.27,
                    negrita=True,
                    punto_final=True,
                ),
                inicio_texto="misma_linea",
            ),
            HeadingConfig(
                nivel=5,
                formato=HeadingFormat(
                    alineacion="izquierda",
                    sangria_cm=1.27,
                    negrita=True,
                    cursiva=True,
                    punto_final=True,
                ),
                inicio_texto="misma_linea",
            ),
        ]
    )
    elementos_documento: DocumentElements = Field(default_factory=DocumentElements)
    citas: CitationRules = Field(default_factory=CitationRules)
    referencias: ReferenceConfig = Field(default_factory=ReferenceConfig)
    tablas_y_figuras: TablesAndFiguresConfig = Field(default_factory=TablesAndFiguresConfig)

    # ----- Optional institutional extensions -----
    metadatos_norma: Optional[InstitutionalMetadata] = None
    referencias_legales_colombia: Optional[ColombianLegalReferences] = None

    # ----- Convenience lookups -----

    @property
    def fuentes_aceptadas(self) -> list[FontConfig]:
        """Shortcut to access accepted fonts list."""
        return self.fuentes_y_tipografia.fuentes_aceptadas

    def get_font(self, nombre: str) -> FontConfig | None:
        """Find a font config by name (case-insensitive)."""
        key = nombre.lower()
        for f in self.fuentes_aceptadas:
            if f.nombre.lower() == key:
                return f
        return None

    def get_heading(self, nivel: int) -> HeadingConfig | None:
        """Find a heading config by level number."""
        for h in self.jerarquia_titulos:
            if h.nivel == nivel:
                return h
        return None

    @property
    def is_institutional(self) -> bool:
        """True if this config has institutional-specific rules."""
        return self.metadatos_norma is not None
