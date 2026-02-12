"""Pydantic models for APA 7 document structure."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from apa_formatter.models.enums import (
    CitationType,
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
    ReferenceType,
)


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
# Citations & References
# ---------------------------------------------------------------------------


class Author(BaseModel):
    """Author information for references."""

    last_name: str
    first_name: str
    middle_initial: Optional[str] = None

    @property
    def apa_format(self) -> str:
        """Format as 'Last, F. M.' for APA reference list."""
        parts = [f"{self.last_name}, {self.first_name[0]}."]
        if self.middle_initial:
            parts[0] = f"{self.last_name}, {self.first_name[0]}. {self.middle_initial}."
        return parts[0]

    @property
    def apa_narrative(self) -> str:
        """Format for narrative citations: 'Last'."""
        return self.last_name


class Reference(BaseModel):
    """A single APA 7 reference entry."""

    ref_type: ReferenceType
    authors: list[Author] = Field(default_factory=list)
    year: Optional[int] = None
    title: str = ""
    source: str = Field("", description="Journal name, publisher, website, etc.")
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    edition: Optional[str] = None
    editors: list[Author] = Field(default_factory=list)
    retrieval_date: Optional[date] = None

    def format_authors_apa(self) -> str:
        """Format author list according to APA 7 rules."""
        if not self.authors:
            return ""

        count = len(self.authors)
        if count == 1:
            return self.authors[0].apa_format
        if count == 2:
            return f"{self.authors[0].apa_format} & {self.authors[1].apa_format}"
        if count <= 20:
            author_strs = [a.apa_format for a in self.authors[:-1]]
            return ", ".join(author_strs) + f", & {self.authors[-1].apa_format}"
        # 21+ authors: first 19, ..., last
        author_strs = [a.apa_format for a in self.authors[:19]]
        return ", ".join(author_strs) + f", ... {self.authors[-1].apa_format}"

    def format_apa(self) -> str:
        """Return the complete APA 7 formatted reference string."""
        parts: list[str] = []

        # Authors
        author_str = self.format_authors_apa()
        if author_str:
            parts.append(author_str)

        # Year
        year_str = f"({self.year})" if self.year else "(n.d.)"
        parts.append(year_str + ".")

        # Title
        if self.ref_type == ReferenceType.JOURNAL_ARTICLE:
            parts.append(f"{self.title}.")
        elif self.ref_type in (ReferenceType.BOOK, ReferenceType.EDITED_BOOK):
            if self.edition:
                parts.append(f"*{self.title}* ({self.edition} ed.).")
            else:
                parts.append(f"*{self.title}*.")
        elif self.ref_type == ReferenceType.BOOK_CHAPTER:
            editor_str = ", ".join(e.apa_format for e in self.editors)
            parts.append(f"{self.title}. In {editor_str} (Eds.),")
            parts.append(f"*{self.source}*")
            if self.pages:
                parts.append(f"(pp. {self.pages}).")
        elif self.ref_type == ReferenceType.WEBPAGE:
            parts.append(f"*{self.title}*.")
        else:
            parts.append(f"{self.title}.")

        # Source (journal name, publisher, etc.)
        if self.ref_type == ReferenceType.JOURNAL_ARTICLE:
            source_str = f"*{self.source}*"
            if self.volume:
                source_str += f", *{self.volume}*"
            if self.issue:
                source_str += f"({self.issue})"
            if self.pages:
                source_str += f", {self.pages}"
            source_str += "."
            parts.append(source_str)
        elif self.ref_type in (ReferenceType.BOOK, ReferenceType.EDITED_BOOK):
            if self.source:
                parts.append(f"{self.source}.")
        elif self.ref_type == ReferenceType.WEBPAGE:
            if self.source:
                parts.append(f"{self.source}.")

        # DOI or URL
        if self.doi:
            parts.append(f"https://doi.org/{self.doi}")
        elif self.url:
            parts.append(self.url)

        return " ".join(parts)


class Citation(BaseModel):
    """An in-text citation."""

    citation_type: CitationType = CitationType.PARENTHETICAL
    authors: list[str] = Field(..., description="Author last names")
    year: Optional[int] = None
    page: Optional[str] = None

    def format_apa(self) -> str:
        """Format the in-text citation according to APA 7."""
        year_str = str(self.year) if self.year else "n.d."

        if len(self.authors) == 1:
            author_str = self.authors[0]
        elif len(self.authors) == 2:
            sep = " & " if self.citation_type == CitationType.PARENTHETICAL else " and "
            author_str = f"{self.authors[0]}{sep}{self.authors[1]}"
        else:
            author_str = f"{self.authors[0]} et al."

        page_str = f", p. {self.page}" if self.page else ""

        if self.citation_type == CitationType.PARENTHETICAL:
            return f"({author_str}, {year_str}{page_str})"
        else:  # NARRATIVE
            return f"{author_str} ({year_str}{page_str})"


# ---------------------------------------------------------------------------
# Full Document
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
