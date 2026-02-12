"""Smart reference parser implementation."""

from __future__ import annotations

import re
from datetime import date
from typing import Union

import bibtexparser
from nameparser import HumanName

from apa_formatter.domain.models.reference import Author, GroupAuthor, Reference
from apa_formatter.domain.models.enums import ReferenceType
from apa_formatter.domain.ports.smart_parser import SmartParserPort
from apa_formatter.infrastructure.fetchers.doi_fetcher import DoiFetcher
from apa_formatter.infrastructure.fetchers.isbn_fetcher import IsbnFetcher
from apa_formatter.infrastructure.fetchers.url_fetcher import UrlFetcher


class SmartReferenceParser(SmartParserPort):
    """Parses raw text into Reference objects using a best-effort strategy."""

    # Regex patterns
    # DOI: 10.xxxx/yyyy
    _DOI_REGEX = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", re.IGNORECASE)
    # ISBN: Loose matching but requires at least 10 chars to avoid matching years/IDs
    _ISBN_REGEX = re.compile(
        r"\b(?:ISBN(?:-1[03])?:? )?(?=[0-9X-]{10,})(?=(?:[0-9]+[- ]){3}[- 0-9X]+)(?:97[89][- ]?)?[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9X]\b",
        re.IGNORECASE,
    )
    # URL: http/https + valid chars (including / and query params)
    _URL_REGEX = re.compile(r"https?://(?:[-\w./?%&=#~+!]+)")
    # Year: 1900-2099 captured fully
    _YEAR_REGEX = re.compile(r"\b((?:19|20)\d{2})\b")

    def __init__(self) -> None:
        self._doi_fetcher = DoiFetcher()
        self._isbn_fetcher = IsbnFetcher()
        self._url_fetcher = UrlFetcher()

    def parse(self, text: str) -> Reference | None:
        """Attempt to parse text into a Reference using fallback strategies."""
        text = text.strip()
        if not text:
            return None

        # Level 1: Deterministic Detection
        ref = self._try_deterministic(text)
        if ref:
            return ref

        # Level 2: Structured Parsing (BibTeX)
        ref = self._try_bibtex(text)
        if ref:
            return ref

        # Level 3: Naive Heuristics
        return self._try_heuristic(text)

    def _try_deterministic(self, text: str) -> Reference | None:
        """Try to find identifier and fetch metadata."""
        # Check DOI
        doi_match = self._DOI_REGEX.search(text)
        if doi_match:
            try:
                return self._doi_fetcher.fetch(doi_match.group(1))
            except Exception:
                pass  # Fallback

        # Check ISBN
        isbn_match = self._ISBN_REGEX.search(text)
        if isbn_match:
            try:
                # Clean ISBN string
                clean_isbn = re.sub(r"[^0-9X]", "", isbn_match.group(0))
                return self._isbn_fetcher.fetch(clean_isbn)
            except Exception:
                pass

        # Check URL
        url_match = self._URL_REGEX.search(text)
        if url_match:
            try:
                return self._url_fetcher.fetch(url_match.group(0))
            except Exception:
                pass

        return None

    def _try_bibtex(self, text: str) -> Reference | None:
        """Try to parse as BibTeX."""
        try:
            # BibTeX parser requires a complete entry structure
            if "@" not in text or "{" not in text:
                return None

            # Simple wrapper if just fields are provided
            to_parse = text
            if not text.lstrip().startswith("@"):
                to_parse = f"@misc{{citation_key, {text}}}"

            # bibtexparser v1.x API: loads() returns BibDatabase
            library = bibtexparser.loads(to_parse)
            if not library.entries:
                return None

            entry = library.entries[0]  # plain dict

            # Extract basic fields
            title = entry.get("title", "Untitled")
            year_str = entry.get("year")
            year = int(year_str) if year_str and year_str.isdigit() else None

            # Determine ref_type from BibTeX ENTRYTYPE
            entry_type = entry.get("ENTRYTYPE", "misc").lower()
            type_map: dict[str, ReferenceType] = {
                "article": ReferenceType.JOURNAL_ARTICLE,
                "book": ReferenceType.BOOK,
                "inbook": ReferenceType.BOOK_CHAPTER,
                "incollection": ReferenceType.BOOK_CHAPTER,
                "inproceedings": ReferenceType.CONFERENCE_PAPER,
                "conference": ReferenceType.CONFERENCE_PAPER,
                "phdthesis": ReferenceType.DISSERTATION,
                "mastersthesis": ReferenceType.DISSERTATION,
                "techreport": ReferenceType.REPORT,
            }
            ref_type = type_map.get(entry_type, ReferenceType.BOOK)

            # Authors
            authors: list[Union[Author, GroupAuthor]] = []
            author_field = entry.get("author")
            if author_field:
                for name in author_field.split(" and "):
                    authors.append(self._parse_human_name(name.strip()))
            else:
                authors.append(Author(first_name="Unknown", last_name="Author"))

            # Source: journal > publisher > booktitle
            source = (
                entry.get("journal")
                or entry.get("publisher")
                or entry.get("booktitle")
                or "Unknown Source"
            )

            return Reference(
                ref_type=ref_type,
                authors=authors,
                year=year,
                title=title,
                source=source,
                volume=entry.get("volume"),
                issue=entry.get("number"),
                pages=entry.get("pages"),
                doi=entry.get("doi"),
                url=entry.get("url"),
                retrieval_date=date.today(),
            )

        except Exception:
            return None

    def _try_heuristic(self, text: str) -> Reference | None:
        """Use simple regex/NLP heuristics to extract fields."""
        # 1. Extract Year
        year = None
        year_matches = self._YEAR_REGEX.findall(text)
        if year_matches:
            year = int(year_matches[-1])  # Use last 4-digit number as likely year

        # 2. Extract Title (naive: text between quotes or first segment)
        title = "Unknown Title"
        if '"' in text:
            parts = text.split('"')
            if len(parts) >= 2:
                title = parts[1]
        else:
            # Assume title is the longest segment if split by dots?
            # Or just take the whole text if short
            if len(text) < 100:
                title = text

        # 3. Extract Author (naive: first segment before date)
        # Using nameparser on the first chunk of text
        first_segment = text.split("(")[0].split(".")[0].strip()
        author = self._parse_human_name(first_segment)

        return Reference(
            ref_type=ReferenceType.BOOK,  # Fallback type
            authors=[author],
            year=year,
            title=title,
            source="Parsed Citation",
            retrieval_date=date.today(),
        )

    def _parse_human_name(self, raw_name: str) -> Author:
        """Parse a human name string into an Author object."""
        name = HumanName(raw_name)
        return Author(
            first_name=name.first + (" " + name.middle if name.middle else ""),
            last_name=name.last,
        )
