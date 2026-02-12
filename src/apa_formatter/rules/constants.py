"""APA 7th Edition formatting constants.

All values are derived from the JSON configuration loaded via
``apa_formatter.config``.  The module exposes the same public names
that the rest of the codebase already imports, so it acts as a
backward-compatible façade.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from apa_formatter.config.loader import get_config
from apa_formatter.models.enums import FontChoice


# ---------------------------------------------------------------------------
# Dataclasses (kept for compatibility with adapters)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FontSpec:
    """Font specification for APA 7."""

    name: str
    size_pt: int


@dataclass(frozen=True)
class HeadingStyle:
    """Style definition for an APA 7 heading level."""

    level: int
    centered: bool
    bold: bool
    italic: bool
    inline: bool  # True = text continues on same line after period
    indent: bool  # True = indented 0.5 inches


# ---------------------------------------------------------------------------
# Derived values (computed from config on first access, then cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_font_specs() -> dict[FontChoice, FontSpec]:
    """Build FONT_SPECS from configuration."""
    cfg = get_config()
    specs: dict[FontChoice, FontSpec] = {}

    name_to_enum: dict[str, FontChoice] = {member.value.lower(): member for member in FontChoice}

    for fc in cfg.fuentes_aceptadas:
        enum_key = name_to_enum.get(fc.nombre.lower())
        if enum_key is not None:
            specs[enum_key] = FontSpec(name=fc.nombre, size_pt=fc.tamaño_pt)

    return specs


@lru_cache(maxsize=1)
def _build_heading_styles() -> dict[int, HeadingStyle]:
    """Build HEADING_STYLES from configuration."""
    cfg = get_config()
    styles: dict[int, HeadingStyle] = {}

    for hc in cfg.jerarquia_titulos:
        styles[hc.nivel] = HeadingStyle(
            level=hc.nivel,
            centered=hc.is_centered,
            bold=hc.is_bold,
            italic=hc.is_italic,
            inline=hc.is_inline,
            indent=hc.is_indented,
        )

    return styles


# ---------------------------------------------------------------------------
# Public constants — these are now dynamically computed properties
# wrapped in a lazy module-level pattern.
# ---------------------------------------------------------------------------


class _LazyConstants:
    """Descriptor-like namespace that lazily reads config values."""

    @property
    def PAPER_WIDTH_INCHES(self) -> float:
        return get_config().configuracion_pagina.tamaño_papel.ancho_inches

    @property
    def PAPER_HEIGHT_INCHES(self) -> float:
        return get_config().configuracion_pagina.tamaño_papel.alto_inches

    @property
    def MARGIN_INCHES(self) -> float:
        return get_config().configuracion_pagina.margenes.superior_inches

    @property
    def MARGIN_CM(self) -> float:
        return get_config().configuracion_pagina.margenes.superior_cm

    @property
    def LINE_SPACING(self) -> float:
        return get_config().formato_texto.interlineado_general

    @property
    def FIRST_LINE_INDENT_INCHES(self) -> float:
        return get_config().formato_texto.sangria_parrafo.medida_inches

    @property
    def HANGING_INDENT_INCHES(self) -> float:
        return get_config().referencias.formato_lista.sangria_francesa_inches

    @property
    def REFERENCES_HEADING(self) -> str:
        return get_config().referencias.formato_lista.titulo

    @property
    def FONT_SPECS(self) -> dict[FontChoice, FontSpec]:
        return _build_font_specs()

    @property
    def HEADING_STYLES(self) -> dict[int, HeadingStyle]:
        return _build_heading_styles()


_lazy = _LazyConstants()

# ---------------------------------------------------------------------------
# Module-level constants (backward-compatible top-level access)
#
# These remain simple values for things that rarely change and are used
# in dozens of call sites.  For values that *must* be lazy (FONT_SPECS,
# HEADING_STYLES), callers already use dict access.
# ---------------------------------------------------------------------------


def _cfg():
    return get_config()


# Page layout
PAPER_WIDTH_INCHES: float = 8.5  # recalculated below
PAPER_HEIGHT_INCHES: float = 11.0

MARGIN_INCHES: float = 1.0  # = 2.54 cm
MARGIN_CM: float = 2.54

# Typography
LINE_SPACING: float = 2.0
FIRST_LINE_INDENT_INCHES: float = 0.5  # 1.27 cm
HANGING_INDENT_INCHES: float = 0.5

# No extra space before or after paragraphs (APA 7 §2.21)
SPACE_BEFORE_PT: int = 0
SPACE_AFTER_PT: int = 0

DEFAULT_FONT = FontChoice.TIMES_NEW_ROMAN

# Title page
TITLE_MAX_WORDS: int = 12
RUNNING_HEAD_MAX_CHARS: int = 50
ABSTRACT_MAX_WORDS: int = 250
TITLE_PAGE_BLANK_LINES_BEFORE_TITLE: int = 3

# Reference list
REFERENCES_HEADING: str = "References"  # overridden at import-time below
APPENDIX_HEADING: str = "Appendix"

# Page numbering
PAGE_NUMBER_START: int = 1
PAGE_NUMBER_POSITION: str = "top-right"


def _apply_config_defaults() -> None:
    """Override module-level constants with values from the JSON config.

    Called once at module import time.
    """
    global PAPER_WIDTH_INCHES, PAPER_HEIGHT_INCHES
    global MARGIN_INCHES, MARGIN_CM
    global LINE_SPACING, FIRST_LINE_INDENT_INCHES, HANGING_INDENT_INCHES
    global REFERENCES_HEADING

    cfg = get_config()
    page = cfg.configuracion_pagina

    PAPER_WIDTH_INCHES = page.tamaño_papel.ancho_inches
    PAPER_HEIGHT_INCHES = page.tamaño_papel.alto_inches
    MARGIN_INCHES = page.margenes.superior_inches
    MARGIN_CM = page.margenes.superior_cm
    LINE_SPACING = cfg.formato_texto.interlineado_general
    FIRST_LINE_INDENT_INCHES = cfg.formato_texto.sangria_parrafo.medida_inches
    HANGING_INDENT_INCHES = cfg.referencias.formato_lista.sangria_francesa_inches
    REFERENCES_HEADING = cfg.referencias.formato_lista.titulo


# Bootstrap on import
_apply_config_defaults()

# Lazy dict accessors -------------------------------------------------------
# These MUST stay as function calls (or use the _lazy helper) because they
# depend on enum mapping logic.  The adapters access them as dicts.

FONT_SPECS: dict[FontChoice, FontSpec] = _build_font_specs()
HEADING_STYLES: dict[int, HeadingStyle] = _build_heading_styles()
