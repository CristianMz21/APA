"""Reference-related domain models for APA 7.

Contains Author, GroupAuthor, Reference, and Citation entities.
These are Pydantic models (pragmatic choice — see implementation plan §6).

This module belongs to the Domain layer. It only depends on:
- Python stdlib (datetime, re, typing)
- Pydantic (pragmatic exception for validation)
- Domain enums (apa_formatter.domain.models.enums)
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Union

import re

from pydantic import BaseModel, Field, field_validator

from apa_formatter.domain.models.enums import (
    CitationType,
    ReferenceType,
)


# ---------------------------------------------------------------------------
# Authors
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


class GroupAuthor(BaseModel):
    """Corporate/organizational author (APA 7 §9.11).

    Group authors are NOT inverted. E.g.:
    - World Health Organization. (2020).
    - American Psychological Association. (2020).
    """

    name: str = Field(..., description="Full organization name (not inverted)")
    abbreviation: Optional[str] = Field(
        None,
        description="Abbreviation for subsequent citations (e.g., WHO, APA)",
    )

    @property
    def apa_format(self) -> str:
        """Return the group name as-is (no inversion per APA 7)."""
        return self.name

    @property
    def apa_narrative(self) -> str:
        """Return group name for narrative citations."""
        return self.name


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


class Reference(BaseModel):
    """A single APA 7 reference entry."""

    ref_type: ReferenceType
    authors: list[Union[Author, GroupAuthor]] = Field(default_factory=list)
    year: Optional[int] = None
    year_suffix: Optional[str] = Field(
        None,
        description="Disambiguation suffix (a, b, c) for same-author-year",
    )
    title: str = ""
    source: str = Field("", description="Journal name, publisher, website, etc.")
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    edition: Optional[str] = None

    @field_validator("doi", mode="before")
    @classmethod
    def _normalize_and_validate_doi(cls, v: str | None) -> str | None:
        """Auto-strip https://doi.org/ prefix and validate DOI format."""
        if v is None:
            return v
        # Strip URL prefix
        v = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", v.strip(), flags=re.IGNORECASE)
        if not re.match(r"^10\.\d{4,9}/[^\s]+$", v):
            raise ValueError(
                f"Invalid DOI format: '{v}'. "
                "Expected pattern: 10.XXXX/... (e.g., 10.1037/amp0000722)"
            )
        return v

    editors: list[Author] = Field(default_factory=list)
    retrieval_date: Optional[date] = None

    # -- Type-specific fields ------------------------------------------------
    conference_location: Optional[str] = Field(
        None,
        description="City, Country for conference papers",
    )
    university: Optional[str] = Field(
        None,
        description="University name for dissertations/theses",
    )
    report_number: Optional[str] = Field(
        None,
        description="Report/document number",
    )
    media_type: Optional[str] = Field(
        None,
        description="Bracketed descriptor: Film, Video, Tweet, Song, etc.",
    )
    platform: Optional[str] = Field(
        None,
        description="Platform name for social media (Twitter, Instagram...)",
    )
    username: Optional[str] = Field(
        None,
        description="Social media handle, e.g. @WHO",
    )
    original_year: Optional[int] = Field(
        None,
        description="Original publication year for translated/republished works",
    )
    locator: Optional[str] = Field(
        None,
        description="Classical-work locator, e.g. 'para. 5' or 'Book II'",
    )

    def format_authors_apa(self) -> str:
        """Format author list according to APA 7 rules.

        Supports both individual ``Author`` and ``GroupAuthor`` instances.
        """
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

    # -- helpers -------------------------------------------------------------

    def _year_str(self, locale: dict[str, str] | None = None) -> str:
        """Return APA-formatted year, including (n.d.) fallback and suffix.

        Handles translated/republished works: ``(1899/2023)``.
        """
        suffix = self.year_suffix or ""
        nd = (locale or {}).get("nd", "n.d.")
        if self.year and self.original_year:
            return f"({self.original_year}/{self.year}{suffix})"
        return f"({self.year}{suffix})" if self.year else f"({nd})"

    def _doi_or_url(self) -> str:
        """Return DOI link or bare URL, or empty string."""
        if self.doi:
            return f"https://doi.org/{self.doi}"
        if self.url:
            return self.url
        return ""

    # -- per-type formatters -------------------------------------------------

    def _fmt_journal_article(self, locale: dict[str, str] | None = None) -> str:
        """Journal article — APA 7 §10.1."""
        parts = self._author_year_parts(locale)
        parts.append(f"{self.title}.")
        source_str = f"*{self.source}*"
        if self.volume:
            source_str += f", *{self.volume}*"
        if self.issue:
            source_str += f"({self.issue})"
        if self.pages:
            source_str += f", {self.pages}"
        source_str += "."
        parts.append(source_str)
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_book(self, locale: dict[str, str] | None = None) -> str:
        """Book / Edited book — APA 7 §10.2.

        Handles compound descriptors: ``(3rd ed., Vol. 2)``.
        """
        L = locale or {}
        parts = self._author_year_parts(locale)
        ed_abbr = L.get("edition_abbr", "ed.")
        vol_abbr = L.get("volume_abbr", "Vol.")
        # Build compound descriptor
        desc_parts: list[str] = []
        if self.edition:
            desc_parts.append(f"{self.edition} {ed_abbr}")
        if self.volume:
            desc_parts.append(f"{vol_abbr} {self.volume}")
        if desc_parts:
            desc = ", ".join(desc_parts)
            parts.append(f"*{self.title}* ({desc}).")
        else:
            parts.append(f"*{self.title}*.")
        if self.source:
            parts.append(f"{self.source}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_book_chapter(self, locale: dict[str, str] | None = None) -> str:
        """Book chapter — APA 7 §10.3."""
        L = locale or {}
        in_word = L.get("in", "In")
        eds_word = L.get("eds", "Eds.")
        pp_abbr = L.get("pages_abbr", "pp.")
        parts = self._author_year_parts(locale)
        editor_str = ", ".join(e.apa_format for e in self.editors)
        parts.append(f"{self.title}. {in_word} {editor_str} ({eds_word}),")
        parts.append(f"*{self.source}*")
        if self.pages:
            parts.append(f"({pp_abbr} {self.pages}).")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_conference_paper(self, locale: dict[str, str] | None = None) -> str:
        """Conference paper / presentation — APA 7 §10.5."""
        L = locale or {}
        parts = self._author_year_parts(locale)
        media = self.media_type or L.get("conference_presentation", "Conference presentation")
        parts.append(f"*{self.title}* [{media}].")
        location_parts: list[str] = []
        if self.source:
            location_parts.append(self.source)
        if self.conference_location:
            location_parts.append(self.conference_location)
        if location_parts:
            parts.append(", ".join(location_parts) + ".")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_dissertation(self, locale: dict[str, str] | None = None) -> str:
        """Dissertation / thesis — APA 7 §10.6."""
        L = locale or {}
        parts = self._author_year_parts(locale)
        desc = self.media_type or L.get("doctoral_dissertation", "Doctoral dissertation")
        uni = self.university or ""
        if uni:
            parts.append(f"*{self.title}* [{desc}, {uni}].")
        else:
            parts.append(f"*{self.title}* [{desc}].")
        if self.source:
            parts.append(f"{self.source}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_report(self, locale: dict[str, str] | None = None) -> str:
        """Report / technical document — APA 7 §10.4."""
        L = locale or {}
        report_label = L.get("report_no", "Report No.")
        parts = self._author_year_parts(locale)
        if self.report_number:
            parts.append(f"*{self.title}* ({report_label} {self.report_number}).")
        else:
            parts.append(f"*{self.title}*.")
        if self.source:
            parts.append(f"{self.source}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_newspaper(self, locale: dict[str, str] | None = None) -> str:
        """Newspaper article — APA 7 §10.1 (periodical variant)."""
        parts = self._author_year_parts(locale)
        parts.append(f"{self.title}.")
        source_str = f"*{self.source}*"
        if self.pages:
            source_str += f", {self.pages}"
        source_str += "."
        parts.append(source_str)
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_magazine(self, locale: dict[str, str] | None = None) -> str:
        """Magazine article — APA 7 §10.1 (periodical variant)."""
        parts = self._author_year_parts(locale)
        parts.append(f"{self.title}.")
        source_str = f"*{self.source}*"
        if self.volume:
            source_str += f", *{self.volume}*"
        if self.issue:
            source_str += f"({self.issue})"
        if self.pages:
            source_str += f", {self.pages}"
        source_str += "."
        parts.append(source_str)
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_webpage(self, locale: dict[str, str] | None = None) -> str:
        """Webpage — APA 7 §10.16."""
        L = locale or {}
        retrieved = L.get("retrieved", "Retrieved")
        from_word = L.get("from", "from")
        parts = self._author_year_parts(locale)
        parts.append(f"*{self.title}*.")
        if self.source:
            parts.append(f"{self.source}.")
        if self.retrieval_date:
            parts.append(f"{retrieved} {self.retrieval_date.strftime('%B %d, %Y')}, {from_word}")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_software(self, locale: dict[str, str] | None = None) -> str:
        """Software / app — APA 7 §10.10."""
        parts = self._author_year_parts(locale)
        title_str = f"*{self.title}*"
        if self.edition:
            title_str += f" (Version {self.edition})"
        media = self.media_type or "Computer software"
        title_str += f" [{media}]."
        parts.append(title_str)
        if self.source:
            parts.append(f"{self.source}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_audiovisual(self, locale: dict[str, str] | None = None) -> str:
        """Audiovisual work (film, TV, podcast, song) — APA 7 §10.12/10.13."""
        parts = self._author_year_parts(locale)
        media = self.media_type or "Film"
        parts.append(f"*{self.title}* [{media}].")
        if self.source:
            parts.append(f"{self.source}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_social_media(self, locale: dict[str, str] | None = None) -> str:
        """Social media post — APA 7 §10.15."""
        parts: list[str] = []
        author_str = self.format_authors_apa()
        if author_str and self.username:
            parts.append(f"{author_str} [{self.username}].")
        elif author_str:
            parts.append(author_str)
        elif self.username:
            parts.append(f"{self.username}.")

        if not parts:
            media = self.media_type or "Post"
            parts.append(f"{self._year_str(locale)}.")
            parts.append(f"{self.title} [{media}].")
            if self.platform:
                parts.append(f"{self.platform}.")
            link = self._doi_or_url()
            if link:
                parts.append(link)
            return " ".join(parts)

        parts.append(f"{self._year_str(locale)}.")
        media = self.media_type or "Post"
        parts.append(f"{self.title} [{media}].")
        if self.platform:
            parts.append(f"{self.platform}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    def _fmt_legal(self, locale: dict[str, str] | None = None) -> str:
        """Legal reference — Bluebook / APA 7 §11."""
        L = locale or {}
        nd = L.get("nd", "n.d.")
        parts: list[str] = []
        parts.append(f"{self.title},")
        if self.source:
            parts.append(self.source)
        if self.volume:
            parts.append(f"§ {self.volume}")
        parts.append(f"({self.year})." if self.year else f"({nd}).")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)

    # -- main dispatch -------------------------------------------------------

    def _author_year_parts(self, locale: dict[str, str] | None = None) -> list[str]:
        """Build the common [Author. (Year).] prefix."""
        parts: list[str] = []
        author_str = self.format_authors_apa()
        if author_str:
            parts.append(author_str)
        parts.append(f"{self._year_str(locale)}.")
        return parts

    def format_apa(self, locale: dict[str, str] | None = None) -> str:
        """Return the complete APA 7 formatted reference string.

        Args:
            locale: Optional dict of localized strings (from ``get_locale()``).
                    Defaults to English if not provided.
        """
        # Legal references have a unique structure (no standard author-year).
        if self.ref_type == ReferenceType.LEGAL:
            return self._fmt_legal(locale)

        formatter_map = {
            ReferenceType.JOURNAL_ARTICLE: self._fmt_journal_article,
            ReferenceType.BOOK: self._fmt_book,
            ReferenceType.EDITED_BOOK: self._fmt_book,
            ReferenceType.BOOK_CHAPTER: self._fmt_book_chapter,
            ReferenceType.CONFERENCE_PAPER: self._fmt_conference_paper,
            ReferenceType.DISSERTATION: self._fmt_dissertation,
            ReferenceType.REPORT: self._fmt_report,
            ReferenceType.NEWSPAPER: self._fmt_newspaper,
            ReferenceType.MAGAZINE: self._fmt_magazine,
            ReferenceType.WEBPAGE: self._fmt_webpage,
            ReferenceType.SOFTWARE: self._fmt_software,
            ReferenceType.AUDIOVISUAL: self._fmt_audiovisual,
            ReferenceType.SOCIAL_MEDIA: self._fmt_social_media,
        }

        formatter = formatter_map.get(self.ref_type)
        if formatter:
            return formatter(locale)

        # Fallback for any future/unknown types
        parts = self._author_year_parts(locale)
        parts.append(f"{self.title}.")
        link = self._doi_or_url()
        if link:
            parts.append(link)
        return " ".join(parts)


# ---------------------------------------------------------------------------
# Citation
# ---------------------------------------------------------------------------


class Citation(BaseModel):
    """An in-text citation."""

    citation_type: CitationType = CitationType.PARENTHETICAL
    authors: list[str] = Field(..., description="Author last names")
    year: Optional[int] = None
    year_suffix: Optional[str] = Field(
        None,
        description="Disambiguation suffix (a, b, c)",
    )
    page: Optional[str] = None

    # -- Secondary citations (APA 7 §8.6) --------------------------------
    is_secondary: bool = Field(
        False,
        description="True if this is a secondary (indirect) citation",
    )
    secondary_author: Optional[str] = Field(
        None,
        description="Author of the secondary source",
    )
    secondary_year: Optional[int] = Field(
        None,
        description="Year of the secondary source",
    )

    # -- Personal communication (APA 7 §8.9) ------------------------------
    communication_date: Optional[str] = Field(
        None,
        description="Date string for personal communication (e.g., 'March 15, 2024')",
    )

    def format_apa(self, locale: dict[str, str] | None = None) -> str:
        """Format the in-text citation according to APA 7."""
        L = locale or {}
        # Personal communication — special format, never in reference list
        if self.citation_type == CitationType.PERSONAL_COMMUNICATION:
            return self._fmt_personal_communication(locale)

        nd = L.get("nd", "n.d.")
        and_word = L.get("and", "and")
        et_al = L.get("et_al", "et al.")
        page_abbr = L.get("page_abbr", "p.")
        as_cited_in = L.get("as_cited_in", "as cited in")

        suffix = self.year_suffix or ""
        year_str = f"{self.year}{suffix}" if self.year else nd

        if len(self.authors) == 1:
            author_str = self.authors[0]
        elif len(self.authors) == 2:
            sep = " & " if self.citation_type == CitationType.PARENTHETICAL else f" {and_word} "
            author_str = f"{self.authors[0]}{sep}{self.authors[1]}"
        else:
            author_str = f"{self.authors[0]} {et_al}"

        page_str = f", {page_abbr} {self.page}" if self.page else ""

        # Secondary citation (as cited in)
        if self.is_secondary and self.secondary_author:
            sec_year = str(self.secondary_year) if self.secondary_year else nd
            cited_in = f"{as_cited_in} {self.secondary_author}, {sec_year}"
            if self.citation_type == CitationType.PARENTHETICAL:
                return f"({author_str}, {year_str}, {cited_in})"
            else:
                return f"{author_str} ({year_str}, {cited_in})"

        if self.citation_type == CitationType.PARENTHETICAL:
            return f"({author_str}, {year_str}{page_str})"
        else:  # NARRATIVE
            return f"{author_str} ({year_str}{page_str})"

    def _fmt_personal_communication(self, locale: dict[str, str] | None = None) -> str:
        """Format personal communication citation (APA 7 §8.9)."""
        L = locale or {}
        pc = L.get("personal_communication", "personal communication")
        nd = L.get("nd", "n.d.")
        author_str = self.authors[0] if self.authors else "Unknown"
        date_str = self.communication_date or nd
        return f"({author_str}, {pc}, {date_str})"
