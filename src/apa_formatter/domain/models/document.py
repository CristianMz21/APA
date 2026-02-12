"""Document structure models for APA 7.

Contains TitlePage, Section, and APADocument — the aggregate root.

This module belongs to the Domain layer. It only depends on:
- Python stdlib (datetime, typing)
- Pydantic (pragmatic exception for validation)
- Domain enums and reference models
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from apa_formatter.domain.models.enums import (
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
)
from apa_formatter.domain.models.reference import Reference


# ---------------------------------------------------------------------------
# Title Page
# ---------------------------------------------------------------------------


class TitlePage(BaseModel):
    """APA 7 title page (student or professional variant)."""

    title: str = Field(..., description="Paper title (bold, centered, title case)")
    authors: list[str] = Field(..., min_length=1, description="Author name(s)")
    affiliation: str = Field(..., description="Institutional affiliation")
    course: Optional[str] = Field(None, description="Course number and name (student)")
    instructor: Optional[str] = Field(None, description="Instructor name (student)")
    due_date: Optional[date] = Field(None, description="Assignment due date (student)")
    running_head: Optional[str] = Field(
        None,
        max_length=50,
        description="Running head (professional only, ≤50 chars)",
    )
    author_note: Optional[str] = Field(None, description="Author note (professional)")
    variant: DocumentVariant = DocumentVariant.STUDENT


# ---------------------------------------------------------------------------
# Sections & Headings
# ---------------------------------------------------------------------------


class Section(BaseModel):
    """A document section with optional heading and content."""

    heading: Optional[str] = Field(None, description="Section heading text")
    level: HeadingLevel = HeadingLevel.LEVEL_1
    content: str = Field("", description="Paragraph text for this section")
    subsections: list[Section] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Full Document (Aggregate Root)
# ---------------------------------------------------------------------------


class APADocument(BaseModel):
    """Complete APA 7 document model."""

    title_page: TitlePage
    abstract: Optional[str] = Field(
        None, max_length=2500, description="Abstract (≤250 words, ~2500 chars)"
    )
    keywords: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    appendices: list[Section] = Field(default_factory=list)

    # Formatting preferences
    font: FontChoice = FontChoice.TIMES_NEW_ROMAN
    output_format: OutputFormat = OutputFormat.DOCX
    include_toc: bool = Field(False, description="Include Table of Contents page")
