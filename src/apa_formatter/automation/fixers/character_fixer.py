"""Character normalisation fixer.

APA 7 / typographic rules:
  • Straight double quotes "…" → smart quotes "…"
  • Straight single quotes '…' → smart quotes '…'
  • Hyphen used as an incidental dash (space-hyphen-space) → em dash (—)
  • Double hyphen (--) → em dash (—)
  • Ellipsis (...) → proper ellipsis (…) — but only 3 dots
"""

from __future__ import annotations

import re

from apa_formatter.automation.base import BaseFixer, FixCategory, FixResult


class CharacterFixer(BaseFixer):
    """Replace straight quotes and hyphens with typographic equivalents."""

    @property
    def name(self) -> str:
        return "Character Fixer"

    @property
    def category(self) -> FixCategory:
        return FixCategory.CHARACTER

    # -- Patterns --------------------------------------------------------

    # Em dash: " - " or "--"
    _SPACED_HYPHEN = re.compile(r"\s+-\s+")
    _DOUBLE_HYPHEN = re.compile(r"--")

    # Ellipsis: exactly 3 dots (not part of a longer run)
    _THREE_DOTS = re.compile(r"(?<!\.)\.{3}(?!\.)")

    def fix(self, text: str) -> FixResult:
        entries = []

        # 1) Smart double quotes
        text, n = self._fix_double_quotes(text)
        if n:
            entries.append(
                self._entry('Comillas rectas (") convertidas a tipográficas ()', count=n)
            )

        # 2) Smart single quotes
        text, n = self._fix_single_quotes(text)
        if n:
            entries.append(
                self._entry("Comillas simples (') convertidas a tipográficas ('')", count=n)
            )

        # 3) Spaced hyphen → em dash
        text, n = self._SPACED_HYPHEN.subn(" — ", text)
        if n:
            entries.append(
                self._entry(
                    "Guion con espacios ( - ) convertido a guion largo (—)",
                    count=n,
                )
            )

        # 4) Double hyphen → em dash
        text, n = self._DOUBLE_HYPHEN.subn("—", text)
        if n:
            entries.append(self._entry("Doble guion (--) convertido a guion largo (—)", count=n))

        # 5) Three dots → ellipsis
        text, n = self._THREE_DOTS.subn("…", text)
        if n:
            entries.append(self._entry("Tres puntos (...) convertidos a elipsis (…)", count=n))

        return FixResult(text=text, entries=entries)

    # -- Smart quote helpers ---------------------------------------------

    @staticmethod
    def _fix_double_quotes(text: str) -> tuple[str, int]:
        """Replace paired straight double quotes with smart quotes.

        Strategy: scan left-to-right, toggling open/close state.
        """
        result: list[str] = []
        count = 0
        expecting_close = False

        for ch in text:
            if ch == '"':
                # Already smart → skip
                if expecting_close:
                    result.append("\u201d")  # "
                else:
                    result.append("\u201c")  # "
                expecting_close = not expecting_close
                count += 1
            else:
                result.append(ch)

        return "".join(result), count // 2 if count else 0

    @staticmethod
    def _fix_single_quotes(text: str) -> tuple[str, int]:
        """Replace paired straight single quotes with smart quotes.

        Only targets clear pairs (not apostrophes).
        Heuristic: a quote preceded by whitespace or at start of line is an opener.
        """
        result: list[str] = []
        count = 0
        i = 0
        chars = list(text)
        length = len(chars)

        while i < length:
            ch = chars[i]
            if ch == "'":
                # Determine if opener or closer / apostrophe
                prev = chars[i - 1] if i > 0 else " "
                if prev in (" ", "\n", "\t", "(", "[", "{", "\u201c"):
                    result.append("\u2018")  # '
                    count += 1
                else:
                    # Could be apostrophe — check if there is a matching close ahead
                    ahead = text[i + 1 :] if i + 1 < length else ""
                    if "'" in ahead:
                        result.append("\u2019")  # '
                        count += 1
                    else:
                        result.append(ch)  # Leave as apostrophe
            else:
                result.append(ch)
            i += 1

        return "".join(result), count // 2 if count else 0
