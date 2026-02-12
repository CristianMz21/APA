"""Whitespace normalisation fixer.

APA 7 rules enforced:
  • Single space after sentence-ending punctuation (not double)
  • No redundant blank lines (max 1 consecutive)
  • Single space between words (no runs of whitespace)
  • Trailing whitespace stripped per line
"""

from __future__ import annotations

import re

from apa_formatter.automation.base import BaseFixer, FixCategory, FixResult


class WhitespaceFixer(BaseFixer):
    """Normalise whitespace to APA 7 conventions."""

    @property
    def name(self) -> str:
        return "Whitespace Fixer"

    @property
    def category(self) -> FixCategory:
        return FixCategory.WHITESPACE

    # -- Patterns --------------------------------------------------------

    _DOUBLE_SPACE_AFTER_PUNCT = re.compile(r"([.!?])  +")
    _MULTI_SPACE = re.compile(r"[^\S\n]{2,}")  # 2+ horizontal spaces
    _TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)
    _MULTI_NEWLINE = re.compile(r"\n{3,}")  # 3+ newlines → 2

    def fix(self, text: str) -> FixResult:
        entries = []

        # 1) Double spaces after punctuation → single
        text, n = self._DOUBLE_SPACE_AFTER_PUNCT.subn(r"\1 ", text)
        if n:
            entries.append(
                self._entry(
                    "Espacios dobles después de puntuación reducidos a uno",
                    count=n,
                )
            )

        # 2) Multiple horizontal spaces → single (must run AFTER #1)
        text, n = self._MULTI_SPACE.subn(" ", text)
        if n:
            entries.append(
                self._entry(
                    "Múltiples espacios entre palabras reducidos a uno",
                    count=n,
                )
            )

        # 3) Trailing whitespace
        text, n = self._TRAILING_WS.subn("", text)
        if n:
            entries.append(self._entry("Espacios en blanco al final de línea eliminados", count=n))

        # 4) Excessive blank lines (keep max 1 blank)
        text, n = self._MULTI_NEWLINE.subn("\n\n", text)
        if n:
            entries.append(
                self._entry(
                    "Saltos de línea redundantes reducidos (máx. 1 línea en blanco)",
                    count=n,
                )
            )

        return FixResult(text=text, entries=entries)
