"""Base interface for APA fixers and shared result types.

Every fixer follows the same contract:
  1. Receives raw text
  2. Returns corrected text + a list of FixEntry logs
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class FixCategory(str, Enum):
    """Broad category a fix belongs to."""

    WHITESPACE = "whitespace"
    CHARACTER = "character"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CITATION = "citation"
    REFERENCE = "reference"


@dataclass
class FixEntry:
    """Single logged correction."""

    category: FixCategory
    message: str
    count: int = 1
    detail: str = ""

    def __str__(self) -> str:
        if self.count > 1:
            return f"[{self.category.value}] {self.message} (×{self.count})"
        return f"[{self.category.value}] {self.message}"


@dataclass
class FixResult:
    """Combined output of a fixer or the full pipeline."""

    text: str
    entries: list[FixEntry] = field(default_factory=list)

    @property
    def total_fixes(self) -> int:
        return sum(e.count for e in self.entries)

    def summary(self) -> str:
        """Human-readable summary of all corrections."""
        if not self.entries:
            return "No se realizaron correcciones."
        lines = [str(e) for e in self.entries]
        lines.append(f"\nTotal de correcciones aplicadas: {self.total_fixes}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseFixer(ABC):
    """Abstract base for every APA fixer in the pipeline.

    Subclasses must implement ``fix(text) -> FixResult``.
    The pipeline calls fixers in order, piping text through each one.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name used in reports."""

    @property
    @abstractmethod
    def category(self) -> FixCategory:
        """Category of corrections this fixer applies."""

    @abstractmethod
    def fix(self, text: str) -> FixResult:
        """Apply corrections to *text* and return a ``FixResult``."""

    # Convenience helper used by concrete fixers
    def _entry(self, message: str, count: int = 1, detail: str = "") -> FixEntry:
        return FixEntry(
            category=self.category,
            message=message,
            count=count,
            detail=detail,
        )
