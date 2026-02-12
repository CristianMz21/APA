"""Fetch journal article metadata from CrossRef by DOI."""

from __future__ import annotations

import re
from typing import Optional

import requests

from apa_formatter.models.document import Author, Reference
from apa_formatter.models.enums import ReferenceType


class DOINotFoundError(Exception):
    """Raised when the DOI is not found in CrossRef."""


class DOIFetchError(Exception):
    """Raised when the CrossRef API request fails."""


_DOI_URL_PREFIX = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)
_DOI_REGEX = re.compile(r"^10\.\d{4,9}/[^\s]+$")
_TIMEOUT = 10  # seconds


def normalize_doi(doi: str) -> str:
    """Strip ``https://doi.org/`` prefix if present, returning the bare DOI."""
    return _DOI_URL_PREFIX.sub("", doi.strip())


def validate_doi(doi: str) -> bool:
    """Return True if *doi* matches the standard DOI format ``10.XXXX/...``."""
    return bool(_DOI_REGEX.match(doi))


def fetch_by_doi(doi: str) -> Reference:
    """Fetch article metadata from CrossRef and return an APA Reference.

    Args:
        doi: A DOI string (bare or full URL — gets auto-normalized).

    Returns:
        A ``Reference`` pre-populated with article metadata.

    Raises:
        DOINotFoundError: DOI not found in CrossRef.
        DOIFetchError: Network/API error.
    """
    bare = normalize_doi(doi)
    url = f"https://api.crossref.org/works/{bare}"

    try:
        resp = requests.get(
            url,
            timeout=_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        if resp.status_code == 404:
            raise DOINotFoundError(f"DOI {bare} not found in CrossRef")
        resp.raise_for_status()
    except requests.RequestException as exc:
        if isinstance(exc, DOINotFoundError):
            raise
        raise DOIFetchError(f"CrossRef request failed: {exc}") from exc

    message = resp.json().get("message", {})

    # Parse authors
    authors: list[Author] = []
    for author_data in message.get("author", []):
        given = author_data.get("given", "")
        family = author_data.get("family", "")
        if given and family:
            authors.append(Author(first_name=given, last_name=family))

    # Parse year
    year: Optional[int] = None
    date_parts = message.get("published-print", message.get("published-online", {}))
    if date_parts and date_parts.get("date-parts"):
        parts = date_parts["date-parts"][0]
        if parts:
            year = parts[0]

    # Parse title
    titles = message.get("title", [])
    title = titles[0] if titles else ""

    # Parse journal
    journals = message.get("container-title", [])
    source = journals[0] if journals else ""

    # Parse volume, issue, pages
    volume = message.get("volume")
    issue = message.get("issue")
    pages = message.get("page")

    return Reference(
        ref_type=ReferenceType.JOURNAL_ARTICLE,
        authors=authors,
        year=year,
        title=title,
        source=source,
        volume=volume,
        issue=issue,
        pages=pages,
        doi=bare,
    )
