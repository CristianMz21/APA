"""Heading detection and formatting fixer.

APA 7 heading levels:
  Level 1 — Centered, Bold, Title Case
  Level 2 — Flush Left, Bold, Title Case
  Level 3 — Flush Left, Bold Italic, Title Case

Heuristics used for detection:
  • Lines shorter than MAX_HEADING_LEN that are followed by a blank line
  • Lines that are UPPER CASE → likely Level 1
  • Short bold-like lines (already wrapped in **…**) → classify by context
  • Lines that match known section names (Introduction, Method, Results, …)
"""

from __future__ import annotations

import re

from apa_formatter.automation.base import BaseFixer, FixCategory, FixResult

MAX_HEADING_LEN = 80

# Known APA sections for strong heading detection
_KNOWN_L1_EN = {
    "abstract",
    "introduction",
    "method",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "appendix",
    "appendices",
}
_KNOWN_L1_ES = {
    "resumen",
    "introducción",
    "introduccion",
    "método",
    "metodo",
    "métodos",
    "metodos",
    "resultados",
    "discusión",
    "discusion",
    "conclusión",
    "conclusion",
    "conclusiones",
    "referencias",
    "apéndice",
    "apendice",
    "apéndices",
    "apendices",
    "bibliografía",
    "bibliografia",
}
_KNOWN_L1 = _KNOWN_L1_EN | _KNOWN_L1_ES

# Minor words NOT capitalised in Title Case (APA rule)
_MINOR_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "if",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "up",
    "yet",
    # Spanish
    "y",
    "e",
    "o",
    "u",
    "de",
    "del",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "en",
    "con",
    "por",
    "para",
    "al",
    "que",
}


class HeadingDetector(BaseFixer):
    """Detect and format document headings per APA 7 levels."""

    @property
    def name(self) -> str:
        return "Heading Detector"

    @property
    def category(self) -> FixCategory:
        return FixCategory.HEADING

    def fix(self, text: str) -> FixResult:
        lines = text.split("\n")
        result_lines: list[str] = []
        entries = []
        l1 = l2 = l3 = 0
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                result_lines.append(line)
                i += 1
                continue

            # Already a markdown heading?
            md_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if md_match:
                level = len(md_match.group(1))
                heading_text = md_match.group(2).strip()
                heading_text = self._to_title_case(heading_text)
                if level == 1:
                    l1 += 1
                elif level == 2:
                    l2 += 1
                else:
                    l3 += 1
                result_lines.append(f"{'#' * level} {heading_text}")
                i += 1
                continue

            # Check if this looks like a heading
            level = self._detect_level(stripped, lines, i)
            if level:
                clean = self._strip_bold(stripped)
                clean = self._to_title_case(clean)
                prefix = "#" * level
                result_lines.append(f"{prefix} {clean}")
                if level == 1:
                    l1 += 1
                elif level == 2:
                    l2 += 1
                else:
                    l3 += 1
                i += 1
                continue

            result_lines.append(line)
            i += 1

        if l1:
            entries.append(self._entry(f"Se detectaron {l1} título(s) Nivel 1", count=l1))
        if l2:
            entries.append(self._entry(f"Se detectaron {l2} título(s) Nivel 2", count=l2))
        if l3:
            entries.append(self._entry(f"Se detectaron {l3} título(s) Nivel 3", count=l3))

        return FixResult(text="\n".join(result_lines), entries=entries)

    # -- Detection heuristics --------------------------------------------

    def _detect_level(self, line: str, lines: list[str], idx: int) -> int | None:
        """Return heading level (1-3) or None if line is not a heading."""
        clean = self._strip_bold(line)
        lower = clean.lower().strip(".:;")

        # Too long to be a heading
        if len(clean) > MAX_HEADING_LEN:
            return None

        # Must be followed by blank line or end of doc (heading convention)
        next_line_blank = (idx + 1 >= len(lines)) or (not lines[idx + 1].strip())
        prev_line_blank = (idx == 0) or (not lines[idx - 1].strip())

        if not next_line_blank:
            return None

        # Level 1: known heading names OR all-uppercase short lines
        if lower in _KNOWN_L1:
            return 1
        if clean.isupper() and len(clean) < 60 and prev_line_blank:
            return 1

        # Level 2: bold-wrapped + preceded by blank line
        is_bold = line.startswith("**") and line.endswith("**")
        if is_bold and prev_line_blank and len(clean) < 60:
            return 2

        # Level 3: italic-bold or just italic-wrapped
        is_bold_italic = line.startswith("***") and line.endswith("***")
        is_italic = line.startswith("*") and line.endswith("*") and not is_bold
        if (is_bold_italic or is_italic) and prev_line_blank:
            return 3

        return None

    # -- Helpers ---------------------------------------------------------

    @staticmethod
    def _strip_bold(text: str) -> str:
        """Remove markdown bold/italic markers."""
        text = text.strip()
        if text.startswith("***") and text.endswith("***"):
            return text[3:-3].strip()
        if text.startswith("**") and text.endswith("**"):
            return text[2:-2].strip()
        if text.startswith("*") and text.endswith("*"):
            return text[1:-1].strip()
        return text

    @staticmethod
    def _to_title_case(text: str) -> str:
        """APA-compliant Title Case: capitalise every word except minor words.

        The first and last word are ALWAYS capitalised.
        Words after a colon are capitalised.
        Handles ALL-CAPS input by lowercasing first.
        """
        words = text.split()
        if not words:
            return text

        result: list[str] = []
        after_colon = False

        for idx, word in enumerate(words):
            lower = word.lower()
            clean_lower = lower.rstrip(".:;,")

            is_first = idx == 0
            is_last = idx == len(words) - 1

            if is_first or is_last or after_colon or clean_lower not in _MINOR_WORDS:
                # Capitalise: lowercase the whole word first, then upper the first char
                result.append(lower[0].upper() + lower[1:] if lower else word)
            else:
                result.append(lower)

            after_colon = word.endswith(":")

        return " ".join(result)
