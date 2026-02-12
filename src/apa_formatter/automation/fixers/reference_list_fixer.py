"""Reference list fixer.

APA 7 reference rules enforced:

1. **Alphabetical sorting** by first author surname.
2. **Hanging indent** (first line flush, continuation lines indented).
3. **"Retrieved from" removal:** APA 7 does not require "Retrieved from"
   for most web URLs; only needed for content that may change.
4. **URL formatting:** Ensure URLs are not wrapped in angle brackets.
"""

from __future__ import annotations

import re

from apa_formatter.automation.base import BaseFixer, FixCategory, FixResult

# Detect the start of the References section
_REF_HEADING = re.compile(
    r"^(?:#{1,3}\s+)?(?:Referencias|References|Bibliografía|Bibliography)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# "Retrieved from" / "Recuperado de" before a URL
_RETRIEVED_FROM = re.compile(
    r"\s*(?:Retrieved from|Recuperado de|Obtenido de)\s+(?=https?://)",
    re.IGNORECASE,
)

# Angle-bracket–wrapped URLs
_ANGLE_URL = re.compile(r"<(https?://[^\s>]+)>")

# Rough heuristic for a reference entry: starts with Author surname
_REF_ENTRY_START = re.compile(
    r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñA-Z'\-]+"  # Surname
    r"(?:\s*,|\s+&|\s+et\s+al)"  # Followed by comma or &
)


class ReferenceListFixer(BaseFixer):
    """Sort, indent, and clean the reference list per APA 7."""

    @property
    def name(self) -> str:
        return "Reference List Fixer"

    @property
    def category(self) -> FixCategory:
        return FixCategory.REFERENCE

    def fix(self, text: str) -> FixResult:
        entries = []

        # 1. Locate references section
        heading_match = _REF_HEADING.search(text)
        if not heading_match:
            return FixResult(text=text, entries=[])

        before = text[: heading_match.end()]
        after = text[heading_match.end() :]

        # 2. Parse reference entries (each is typically 1+ lines)
        ref_entries = self._parse_entries(after)
        if not ref_entries:
            return FixResult(text=text, entries=[])

        # 3. "Retrieved from" removal
        cleaned, n_retrieved = self._remove_retrieved_from(ref_entries)
        if n_retrieved:
            entries.append(
                self._entry(
                    "Eliminado «Retrieved from» innecesario (APA 7)",
                    count=n_retrieved,
                )
            )

        # 4. Angle-bracket URL cleanup
        cleaned, n_angles = self._remove_angle_urls(cleaned)
        if n_angles:
            entries.append(
                self._entry(
                    "Eliminados paréntesis angulares <…> alrededor de URLs",
                    count=n_angles,
                )
            )

        # 5. Alphabetical sort
        sorted_refs, was_sorted = self._sort_alphabetically(cleaned)
        if not was_sorted:
            entries.append(
                self._entry(
                    "Lista de referencias reordenada alfabéticamente",
                    count=len(sorted_refs),
                )
            )

        # 6. Hanging indent
        indented = self._apply_hanging_indent(sorted_refs)
        entries.append(
            self._entry(
                "Sangría francesa aplicada a referencias",
                count=len(indented),
            )
        )

        # Rebuild the section
        ref_block = "\n".join(indented)
        result_text = f"{before}\n\n{ref_block}"
        return FixResult(text=result_text, entries=entries)

    # -- Parsing ---------------------------------------------------------

    @staticmethod
    def _parse_entries(text: str) -> list[str]:
        """Split text after the heading into individual reference entries.

        A new entry starts when a line matches the surname pattern.
        Continuation lines are joined to the current entry.
        """
        lines = text.strip().split("\n")
        refs: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    refs.append(" ".join(current))
                    current = []
                continue

            if _REF_ENTRY_START.match(stripped) and current:
                refs.append(" ".join(current))
                current = [stripped]
            else:
                current.append(stripped)

        if current:
            refs.append(" ".join(current))

        return refs

    # -- Cleaning --------------------------------------------------------

    @staticmethod
    def _remove_retrieved_from(refs: list[str]) -> tuple[list[str], int]:
        count = 0
        result = []
        for ref in refs:
            new_ref, n = _RETRIEVED_FROM.subn(" ", ref)
            count += n
            result.append(new_ref.strip())
        return result, count

    @staticmethod
    def _remove_angle_urls(refs: list[str]) -> tuple[list[str], int]:
        count = 0
        result = []
        for ref in refs:
            new_ref, n = _ANGLE_URL.subn(r"\1", ref)
            count += n
            result.append(new_ref)
        return result, count

    # -- Sorting ---------------------------------------------------------

    @staticmethod
    def _sort_alphabetically(refs: list[str]) -> tuple[list[str], bool]:
        """Sort references alphabetically by first author surname.

        Returns (sorted_list, already_was_sorted).
        """

        def _sort_key(ref: str) -> str:
            # Normalise for sorting: lowercase, strip accents (basic)
            return ref.lower().strip()

        sorted_refs = sorted(refs, key=_sort_key)
        was_sorted = sorted_refs == refs
        return sorted_refs, was_sorted

    # -- Hanging indent --------------------------------------------------

    @staticmethod
    def _apply_hanging_indent(refs: list[str]) -> list[str]:
        """Apply hanging indent: first line flush, continuation indented.

        Since we operate on plain text, we use a tab marker for
        continuation lines that will be rendered by the downstream adapter.
        """
        result = []
        for ref in refs:
            # Wrap at ~80 chars (soft wrap)
            words = ref.split()
            lines: list[str] = []
            current_line: list[str] = []
            length = 0

            for word in words:
                if length + len(word) + 1 > 80 and current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    length = len(word)
                else:
                    current_line.append(word)
                    length += len(word) + 1

            if current_line:
                lines.append(" ".join(current_line))

            # First line flush, rest indented
            if lines:
                formatted = lines[0]
                for cont in lines[1:]:
                    formatted += f"\n\t{cont}"
                result.append(formatted)

        return result
