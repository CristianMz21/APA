"""APA Auto-Formatter Pipeline.

Orchestrates a chain of ``BaseFixer`` instances to transform raw text
into APA 7th Edition–compliant output.  The pipeline executes fixers in
three phases:

  1. **Input Normalisation** — WhitespaceFixer, CharacterFixer
  2. **Structure Intelligence** — HeadingDetector, ParagraphFixer
  3. **Content Correction** — CitationFixer, ReferenceListFixer

Each fixer is independent and can be added, removed, or reordered.
The pipeline collects a consolidated ``FixResult`` with every correction
logged for user review.
"""

from __future__ import annotations

from apa_formatter.automation.base import BaseFixer, FixResult
from apa_formatter.automation.fixers.character_fixer import CharacterFixer
from apa_formatter.automation.fixers.citation_fixer import CitationFixer
from apa_formatter.automation.fixers.heading_detector import HeadingDetector
from apa_formatter.automation.fixers.paragraph_fixer import ParagraphFixer
from apa_formatter.automation.fixers.reference_list_fixer import ReferenceListFixer
from apa_formatter.automation.fixers.whitespace_fixer import WhitespaceFixer


class APAAutoFormatter:
    """High-level orchestrator that runs all APA fixers in sequence.

    Usage::

        formatter = APAAutoFormatter()
        result = formatter.run(dirty_text)
        print(result.text)     # corrected text
        print(result.summary())  # human-readable change log
    """

    def __init__(self, fixers: list[BaseFixer] | None = None) -> None:
        self._fixers: list[BaseFixer] = fixers or self._default_pipeline()

    # -- Public API ------------------------------------------------------

    def run(self, text: str) -> FixResult:
        """Execute the full pipeline on *text*.

        Returns a ``FixResult`` containing the corrected text and a
        consolidated list of all ``FixEntry`` logs from every fixer.
        """
        all_entries = []

        for fixer in self._fixers:
            result = fixer.fix(text)
            text = result.text
            all_entries.extend(result.entries)

        return FixResult(text=text, entries=all_entries)

    def add_fixer(self, fixer: BaseFixer, *, position: int | None = None) -> None:
        """Insert a custom fixer into the pipeline.

        If *position* is ``None`` the fixer is appended at the end.
        """
        if position is None:
            self._fixers.append(fixer)
        else:
            self._fixers.insert(position, fixer)

    def remove_fixer(self, name: str) -> bool:
        """Remove the first fixer whose ``name`` matches.

        Returns ``True`` if a fixer was removed.
        """
        for i, fixer in enumerate(self._fixers):
            if fixer.name == name:
                self._fixers.pop(i)
                return True
        return False

    @property
    def fixer_names(self) -> list[str]:
        """Names of the currently registered fixers, in order."""
        return [f.name for f in self._fixers]

    # -- Default pipeline ------------------------------------------------

    @staticmethod
    def _default_pipeline() -> list[BaseFixer]:
        """Factory for the standard three-phase APA pipeline."""
        return [
            # Phase 1 — Input Normalisation
            WhitespaceFixer(),
            CharacterFixer(),
            # Phase 2 — Structure Intelligence
            HeadingDetector(),
            ParagraphFixer(),
            # Phase 3 — Content Correction
            CitationFixer(),
            ReferenceListFixer(),
        ]
