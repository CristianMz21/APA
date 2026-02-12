"""User preferences model for APA Formatter.

This module defines the ``UserSettings`` Pydantic model that captures
user-specific preferences (document structure, formatting, system).
These are *separate* from ``APAConfig`` which encodes APA 7 formatting rules.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from apa_formatter.domain.models.enums import ExportFormat, FontFamily, Language


# ---------------------------------------------------------------------------
# Sub-models by semantic category
# ---------------------------------------------------------------------------


class DocumentStructureSettings(BaseModel):
    """User preferences that affect the document structure."""

    force_title_page_break: bool = Field(
        default=True,
        description="Insert a page break after the title page.",
    )
    include_abstract: bool = Field(
        default=True,
        description="Generate space for the abstract section.",
    )
    student_mode: bool = Field(
        default=True,
        description="Student variant (no Running Head) vs. Professional.",
    )


class FormattingSettings(BaseModel):
    """User preferences for visual formatting."""

    font_family: FontFamily = Field(
        default=FontFamily.TIMES_NEW_ROMAN,
        description="Preferred font family.",
    )
    font_size: int = Field(
        default=12,
        ge=8,
        le=24,
        description="Font size in points.",
    )
    line_spacing: float = Field(
        default=2.0,
        ge=1.0,
        le=3.0,
        description="Line spacing multiplier.",
    )


class SystemSettings(BaseModel):
    """Application-level system preferences."""

    language: Language = Field(
        default=Language.ES,
        description="UI language.",
    )
    default_export_format: ExportFormat = Field(
        default=ExportFormat.DOCX,
        description="Default export format when saving documents.",
    )


# ---------------------------------------------------------------------------
# Root settings model
# ---------------------------------------------------------------------------


class UserSettings(BaseModel):
    """Root user preferences — persisted to ``user_settings.json``."""

    document: DocumentStructureSettings = Field(
        default_factory=DocumentStructureSettings,
    )
    formatting: FormattingSettings = Field(
        default_factory=FormattingSettings,
    )
    system: SystemSettings = Field(
        default_factory=SystemSettings,
    )
