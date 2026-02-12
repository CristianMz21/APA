"""Semantic document models for intelligent import analysis.

These models represent the rich, semantically-analyzed output of the
document import pipeline. Unlike the flat ``AnalysisResult`` dataclass,
``SemanticDocument`` maps directly to domain models and provides
auto-detected configuration ready for downstream formatting.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from apa_formatter.config.models import PaperSize
from apa_formatter.domain.models.document import Section
from apa_formatter.domain.models.enums import Language
from apa_formatter.domain.models.reference import Reference


# ---------------------------------------------------------------------------
# Auto-detected configuration
# ---------------------------------------------------------------------------


class DetectedConfig(BaseModel):
    """Configuration values auto-detected from document analysis."""

    language: Language = Language.ES
    page_size: PaperSize | None = None
    has_title_page: bool = False
    has_abstract: bool = False
    detected_fonts: list[str] = Field(default_factory=list)
    line_spacing: float | None = None


# ---------------------------------------------------------------------------
# Title page extraction result
# ---------------------------------------------------------------------------


class TitlePageData(BaseModel):
    """Extracted title page components with confidence score."""

    title: str = "Documento sin título"
    authors: list[str] = Field(default_factory=lambda: ["Autor desconocido"])
    affiliation: str | None = None
    course: str | None = None
    instructor: str | None = None
    date_text: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Semantic Document  — the rich import result
# ---------------------------------------------------------------------------


class SemanticDocument(BaseModel):
    """Rich semantic representation of an imported document.

    Produced by the ``SemanticImporter`` pipeline (parser → handler
    chain → builder).  Maps directly to domain models for immediate
    downstream formatting.
    """

    title_page: TitlePageData | None = None
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    body_sections: list[Section] = Field(default_factory=list)
    references_raw: list[str] = Field(default_factory=list)
    references_parsed: list[Reference] = Field(default_factory=list)
    detected_config: DetectedConfig = Field(default_factory=DetectedConfig)
    source_path: str = ""
