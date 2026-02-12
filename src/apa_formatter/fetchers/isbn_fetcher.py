"""Fetch book metadata from Open Library by ISBN."""

from __future__ import annotations

import re
from typing import Optional

import requests

from apa_formatter.models.document import Author, Reference
from apa_formatter.models.enums import ReferenceType


class ISBNNotFoundError(Exception):
    """Raised when the ISBN is not found in Open Library."""


class ISBNFetchError(Exception):
    """Raised when the Open Library API request fails."""


_ISBN_CLEAN_RE = re.compile(r"[^0-9Xx]")
_TIMEOUT = 10  # seconds


def _clean_isbn(isbn: str) -> str:
    """Strip hyphens and spaces from an ISBN string."""
    return _ISBN_CLEAN_RE.sub("", isbn)


def fetch_by_isbn(isbn: str) -> Reference:
    """Fetch book metadata from Open Library and return an APA Reference.

    Args:
        isbn: ISBN-10 or ISBN-13 (hyphens/spaces are stripped automatically).

    Returns:
        A ``Reference`` pre-populated with book data.

    Raises:
        ISBNNotFoundError: ISBN not found in Open Library.
        ISBNFetchError: Network/API error.
    """
    clean = _clean_isbn(isbn)
    key = f"ISBN:{clean}"
    url = f"https://openlibrary.org/api/books?bibkeys={key}&format=json&jscmd=data"

    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ISBNFetchError(f"Open Library request failed: {exc}") from exc

    data = resp.json()
    if key not in data:
        raise ISBNNotFoundError(f"ISBN {clean} not found in Open Library")

    book = data[key]

    # Parse authors
    authors: list[Author] = []
    for author_data in book.get("authors", []):
        name = author_data.get("name", "")
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            authors.append(Author(first_name=parts[0], last_name=parts[1]))
        else:
            authors.append(Author(first_name=name, last_name=name))

    # Parse year
    year: Optional[int] = None
    pub_date = book.get("publish_date", "")
    year_match = re.search(r"\b(\d{4})\b", pub_date)
    if year_match:
        year = int(year_match.group(1))

    # Parse publisher
    publishers = book.get("publishers", [])
    source = publishers[0].get("name", "") if publishers else ""

    return Reference(
        ref_type=ReferenceType.BOOK,
        authors=authors,
        year=year,
        title=book.get("title", ""),
        source=source,
        url=book.get("url", None),
    )
