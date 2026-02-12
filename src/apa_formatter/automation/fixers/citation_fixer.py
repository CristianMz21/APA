"""In-text citation fixer.

APA 7 citation rules enforced:

1. **Narrative citation fix:**
   "Según (Smith, 2020)…" → "Según Smith (2020)…"

2. **Page locator fix:**
   "(Smith, 2020, p12)"  → "(Smith, 2020, p. 12)"
   "(Smith, 2020, pp12-20)" → "(Smith, 2020, pp. 12-20)"

3. **Et al. rule:**
   On second+ mention of a citation with 3+ authors, suggest "et al."
   E.g. "(Smith, Jones, & Lee, 2020)" second time → "(Smith et al., 2020)"

4. **Ampersand rule:**
   Inside parenthetical citations: use "&"
   Narrative citations: use "y" / "and"
"""

from __future__ import annotations

import re
from collections import Counter

from apa_formatter.automation.base import BaseFixer, FixCategory, FixResult


class CitationFixer(BaseFixer):
    """Fix common in-text citation errors per APA 7."""

    @property
    def name(self) -> str:
        return "Citation Fixer"

    @property
    def category(self) -> FixCategory:
        return FixCategory.CITATION

    # -- Patterns --------------------------------------------------------

    # Matches "(Author(s), YYYY)" possibly with page info
    # Captures multi-author groups like "Smith, Jones, & Lee"
    _PAREN_CITE = re.compile(
        r"\("
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñA-Z.\-&, ]+?)"  # Author(s) incl. & and ,
        r",\s*"
        r"(\d{4}[a-z]?)"  # Year + optional letter
        r"(?:,\s*(.*?))?"  # Optional locator
        r"\)"
    )

    # Narrative pattern: "Según (Author, Year)" → "Según Author (Year)"
    _NARRATIVE_CUE = re.compile(
        r"((?:según|para|como señala|de acuerdo con|"
        r"according to|as stated by|as noted by)\s+)"
        r"\("
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñA-Z.\- ]+?)"
        r",\s*"
        r"(\d{4}[a-z]?)"
        r"\)",
        re.IGNORECASE,
    )

    # Page locator without proper formatting: p12, pp12-20
    _BAD_PAGE = re.compile(r"\b(pp?)(\d+(?:\s*[-–]\s*\d+)?)")

    # Multi-author with "and" / "y" / "&"
    _MULTI_AUTHOR = re.compile(
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)"
        r"(?:\s*,\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*"
        r"\s*(?:[,]?\s*(?:&|y|and)\s+)"
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)"
    )

    def fix(self, text: str) -> FixResult:
        entries = []

        # 1) Narrative cue fix: "Según (Smith, 2020)" → "Según Smith (2020)"
        text, n = self._fix_narrative(text)
        if n:
            entries.append(
                self._entry("Citas narrativas corregidas (autor fuera del paréntesis)", count=n)
            )

        # 2) Page locator fix: "p12" → "p. 12"
        text, n = self._fix_page_locators(text)
        if n:
            entries.append(self._entry("Localizadores de página corregidos (p. / pp.)", count=n))

        # 3) Et al. rule: 3+ authors on 2nd+ mention
        text, n = self._fix_et_al(text)
        if n:
            entries.append(self._entry("Citas con 3+ autores simplificadas a «et al.»", count=n))

        return FixResult(text=text, entries=entries)

    # -- Fix helpers -----------------------------------------------------

    def _fix_narrative(self, text: str) -> tuple[str, int]:
        """'Según (Smith, 2020)' → 'Según Smith (2020)'."""

        def _repl(m: re.Match) -> str:
            cue = m.group(1)
            author = m.group(2)
            year = m.group(3)
            return f"{cue}{author} ({year})"

        return self._NARRATIVE_CUE.subn(_repl, text)

    def _fix_page_locators(self, text: str) -> tuple[str, int]:
        """'p12' → 'p. 12', 'pp12-20' → 'pp. 12-20'."""

        def _repl(m: re.Match) -> str:
            prefix = m.group(1)  # "p" or "pp"
            numbers = m.group(2)  # "12" or "12-20"
            # Normalise dash
            numbers = re.sub(r"\s*[-–]\s*", "–", numbers)
            return f"{prefix}. {numbers}"

        return self._BAD_PAGE.subn(_repl, text)

    def _fix_et_al(self, text: str) -> tuple[str, int]:
        """On second+ mention of a 3+ author cite, replace with et al.

        Strategy:
        1. Find all parenthetical cites and extract (first_author, year)
        2. Count occurrences
        3. On second+ occurrence of 3+ author, replace with "FirstAuthor et al., Year"
        """
        # Extract all cites
        all_cites = self._PAREN_CITE.finditer(text)
        seen: Counter[str] = Counter()
        replacements: dict[int, tuple[str, str]] = {}  # start_pos → (old, new)

        for m in all_cites:
            authors_str = m.group(1).strip()
            year = m.group(2)
            locator = m.group(3)

            # Count commas + "&" to determine author count
            comma_count = authors_str.count(",")
            has_and = bool(re.search(r"\b(?:&|and|y)\b", authors_str))
            author_count = comma_count + (1 if has_and else 0) + 1

            if author_count < 3:
                continue

            # Extract first author surname
            first_author = re.split(r"[,&]", authors_str)[0].strip()
            key = f"{first_author}_{year}"
            seen[key] += 1

            if seen[key] >= 2:
                # Build replacement
                loc_part = f", {locator}" if locator else ""
                new_cite = f"({first_author} et al., {year}{loc_part})"
                replacements[m.start()] = (m.group(), new_cite)

        count = 0
        for pos in sorted(replacements, reverse=True):
            old, new = replacements[pos]
            text = text[:pos] + new + text[pos + len(old) :]
            count += 1

        return text, count
