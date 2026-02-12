"""Locale loader for APA formatting internationalization."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_LOCALE_DIR = Path(__file__).parent

# Default English strings (fallback if file is missing)
_DEFAULT_LOCALE: dict[str, str] = {
    "and": "and",
    "et_al": "et al.",
    "nd": "n.d.",
    "retrieved": "Retrieved",
    "from": "from",
    "in": "In",
    "eds": "Eds.",
    "ed": "Ed.",
    "trans": "Trans.",
    "personal_communication": "personal communication",
    "as_cited_in": "as cited in",
    "doctoral_dissertation": "Doctoral dissertation",
    "masters_thesis": "Master's thesis",
    "conference_presentation": "Conference presentation",
    "no_date_parens": "(n.d.)",
    "edition_abbr": "ed.",
    "volume_abbr": "Vol.",
    "pages_abbr": "pp.",
    "page_abbr": "p.",
    "report_no": "Report No.",
}


@lru_cache(maxsize=8)
def get_locale(lang: str = "en") -> dict[str, str]:
    """Load locale strings for the given language code.

    Args:
        lang: ISO 639-1 language code (``en`` or ``es``).

    Returns:
        Dictionary mapping string keys to localized values.
        Falls back to English defaults if the locale file is not found.
    """
    locale_file = _LOCALE_DIR / f"{lang}.json"
    if locale_file.exists():
        with locale_file.open(encoding="utf-8") as f:
            loaded = json.load(f)
        # Merge with defaults so new keys are always available
        merged = {**_DEFAULT_LOCALE, **loaded}
        return merged
    return dict(_DEFAULT_LOCALE)
