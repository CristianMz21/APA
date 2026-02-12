"""Reference list manager with year disambiguation and sorting.

This module belongs to the Domain layer. It only depends on:
- Python stdlib (collections)
- Pydantic (pragmatic exception for validation)
- Domain reference models
"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from apa_formatter.domain.models.reference import GroupAuthor, Reference

# Name prefixes that should be ignored for sorting (APA 7 §9.45)
_NAME_PREFIXES = ("de", "del", "van", "von", "el", "al", "la", "le", "du")


def _strip_prefix(name: str) -> str:
    """Strip common name prefixes for sort-key generation.

    E.g. ``de León`` → ``león``, ``van Gogh`` → ``gogh``.
    """
    lower = name.lower()
    for prefix in _NAME_PREFIXES:
        candidate = prefix + " "
        if lower.startswith(candidate):
            return lower[len(candidate) :]
        # Handle hyphenated prefixes like "al-"
        candidate_hyp = prefix + "-"
        if lower.startswith(candidate_hyp):
            return lower[len(candidate_hyp) :]
    return lower


class ReferenceManager(BaseModel):
    """Manages a collection of APA references.

    Provides:
    - Alphabetical sorting by first author
    - Year disambiguation (a, b, c suffixes per APA 7 §8.19)
    - Formatted reference list output
    """

    references: list[Reference] = Field(default_factory=list)

    # -- CRUD ----------------------------------------------------------------

    def add(self, ref: Reference) -> None:
        """Add a reference and re-run disambiguation."""
        self.references.append(ref)
        self.disambiguate_years()

    def remove(self, index: int) -> None:
        """Remove a reference by index and re-run disambiguation."""
        if 0 <= index < len(self.references):
            self.references.pop(index)
            self.disambiguate_years()

    # -- Sorting -------------------------------------------------------------

    def _sort_key(self, ref: Reference) -> str:
        """Build a sort key from first author last name + year + title."""
        if ref.authors:
            first = ref.authors[0]
            if isinstance(first, GroupAuthor):
                name = _strip_prefix(first.name)
            else:
                name = _strip_prefix(first.last_name)
        else:
            # No author → sort by title (APA 7 §9.47)
            name = ref.title.lower()
        year = str(ref.year) if ref.year else "9999"
        return f"{name}|{year}|{ref.title.lower()}"

    def sort_alphabetically(self) -> None:
        """Sort references alphabetically by first author last name."""
        self.references.sort(key=self._sort_key)

    # -- Year disambiguation -------------------------------------------------

    @staticmethod
    def _author_key(ref: Reference) -> str:
        """Build a canonical author key for collision detection."""
        if not ref.authors:
            return f"__no_author__{ref.title.lower()}"
        parts: list[str] = []
        for author in ref.authors:
            if isinstance(author, GroupAuthor):
                parts.append(author.name.lower())
            else:
                parts.append(f"{author.last_name.lower()},{author.first_name[0].lower()}")
        return "|".join(parts)

    def disambiguate_years(self) -> None:
        """Detect author-year collisions and assign a/b/c suffixes (APA 7 §8.19).

        Resets all suffixes first, then only assigns where collisions exist.
        References are grouped by (author_key, year). Groups of size > 1 are
        sorted by title and assigned sequential suffixes.
        """
        # Reset all suffixes
        for ref in self.references:
            ref.year_suffix = None

        # Group by (author_key, year)
        groups: dict[str, list[Reference]] = defaultdict(list)
        for ref in self.references:
            key = f"{self._author_key(ref)}|{ref.year}"
            groups[key].append(ref)

        # Assign suffixes only where there are collisions
        for refs in groups.values():
            if len(refs) > 1:
                # Sort by title to ensure deterministic ordering
                refs.sort(key=lambda r: r.title.lower())
                for i, ref in enumerate(refs):
                    ref.year_suffix = chr(ord("a") + i)

    # -- Output --------------------------------------------------------------

    def format_reference_list(self, locale: dict[str, str] | None = None) -> str:
        """Return all references formatted as an APA reference list.

        References are sorted alphabetically before formatting.
        """
        self.sort_alphabetically()
        return "\n\n".join(ref.format_apa(locale) for ref in self.references)
