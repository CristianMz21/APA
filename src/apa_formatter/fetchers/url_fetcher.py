"""Fetch webpage metadata by scraping HTML meta tags."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from apa_formatter.models.document import Author, GroupAuthor, Reference
from apa_formatter.models.enums import ReferenceType


class URLFetchError(Exception):
    """Raised when the URL cannot be fetched or parsed."""


_TIMEOUT = 10  # seconds


def _extract_meta(soup: BeautifulSoup, *names: str) -> Optional[str]:
    """Search for the first matching meta tag content."""
    for name in names:
        # Try name attribute
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
        # Try property attribute (Open Graph)
        tag = soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return None


def _parse_author_name(name: str) -> Author:
    """Best-effort parse of a free-text author name."""
    parts = name.strip().rsplit(" ", 1)
    if len(parts) == 2:
        return Author(first_name=parts[0], last_name=parts[1])
    return Author(first_name=name.strip(), last_name=name.strip())


def _parse_year(date_str: str) -> Optional[int]:
    """Extract a 4-digit year from a date string."""
    match = re.search(r"\b(\d{4})\b", date_str)
    return int(match.group(1)) if match else None


def fetch_by_url(url: str) -> Reference:
    """Scrape a webpage for title, author, and date metadata.

    Uses ``<meta>`` tags (Dublin Core, Open Graph, standard HTML meta)
    and falls back to ``<title>`` for the page title.

    Args:
        url: Full URL to scrape.

    Returns:
        A ``Reference`` of type WEBPAGE.

    Raises:
        URLFetchError: Network error or unparseable HTML.
    """
    try:
        resp = requests.get(
            url,
            timeout=_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; APAFormatter/1.0; +https://github.com/apa-formatter)"
                ),
            },
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise URLFetchError(f"Failed to fetch URL: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title = _extract_meta(soup, "og:title", "dc.title", "twitter:title") or (
        soup.title.string.strip() if soup.title and soup.title.string else ""
    )

    # Author
    author_str = _extract_meta(soup, "author", "dc.creator", "article:author")
    authors: list[Author | GroupAuthor] = []
    if author_str:
        authors = [_parse_author_name(author_str)]

    # Date / Year
    date_str = _extract_meta(
        soup,
        "date",
        "dc.date",
        "article:published_time",
        "og:article:published_time",
        "publication_date",
    )
    year: Optional[int] = _parse_year(date_str) if date_str else None

    # Site name
    site_name = _extract_meta(soup, "og:site_name", "application-name") or ""

    return Reference(
        ref_type=ReferenceType.WEBPAGE,
        authors=authors,
        year=year,
        title=title,
        source=site_name,
        url=url,
        retrieval_date=date.today(),
    )
