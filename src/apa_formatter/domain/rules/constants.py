"""APA 7 formatting constants — pure domain values.

These are the immutable, spec-defined values from APA 7.
They have NO dependency on configuration files or external libraries.

Dynamic/config-derived values live in the infrastructure layer
(json_config_provider) and are injected via ConfigProviderPort.
"""

from dataclasses import dataclass

from apa_formatter.domain.models.enums import FontChoice


# ---------------------------------------------------------------------------
# Value Objects (frozen dataclasses)
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
# Pure APA 7 constants (not configuration-dependent)
# ---------------------------------------------------------------------------

# Page layout defaults
PAPER_WIDTH_INCHES: float = 8.5
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
REFERENCES_HEADING: str = "References"
APPENDIX_HEADING: str = "Appendix"

# Page numbering
PAGE_NUMBER_START: int = 1
PAGE_NUMBER_POSITION: str = "top-right"

# Heading styles per APA 7 §2.27
DEFAULT_HEADING_STYLES: dict[int, HeadingStyle] = {
    1: HeadingStyle(level=1, centered=True, bold=True, italic=False, inline=False, indent=False),
    2: HeadingStyle(level=2, centered=False, bold=True, italic=False, inline=False, indent=False),
    3: HeadingStyle(level=3, centered=False, bold=True, italic=True, inline=False, indent=False),
    4: HeadingStyle(level=4, centered=False, bold=True, italic=False, inline=True, indent=True),
    5: HeadingStyle(level=5, centered=False, bold=True, italic=True, inline=True, indent=True),
}
