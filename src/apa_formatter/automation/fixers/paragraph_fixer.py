"""Paragraph formatting fixer.

APA 7 rules:
  • First-line indent of ½ inch (0.5 in / 1.27 cm) for normal paragraphs
  • NO indent on headings, blockquotes, list items, or the first paragraph
    after a heading (depending on style variant)
  • No extra space between paragraphs (handled by the renderer, but this
    fixer marks indent markers for downstream consumers)

Since this fixer operates on **plain text / markdown**, it applies a
soft indent marker: a tab character (\\t) at the start of body paragraphs
when not already present.
"""

from __future__ import annotations

import re

from apa_formatter.automation.base import BaseFixer, FixCategory, FixResult

_HEADING_RE = re.compile(r"^#{1,5}\s")
_LIST_RE = re.compile(r"^[\-\*\d]+[.)]\s")
_BLOCKQUOTE_RE = re.compile(r"^>+\s")


class ParagraphFixer(BaseFixer):
    """Ensure correct first-line indentation on body paragraphs."""

    @property
    def name(self) -> str:
        return "Paragraph Fixer"

    @property
    def category(self) -> FixCategory:
        return FixCategory.PARAGRAPH

    def fix(self, text: str) -> FixResult:
        lines = text.split("\n")
        result: list[str] = []
        entries = []
        indent_count = 0
        prev_blank = True  # Start as if preceded by blank (first para rule)
        last_content_was_heading = False  # Tracks the last NON-BLANK line

        for line in lines:
            stripped = line.strip()

            if not stripped:
                result.append("")
                prev_blank = True
                # Do NOT reset last_content_was_heading — blank lines
                # between heading and body shouldn't clear the flag
                continue

            is_heading = bool(_HEADING_RE.match(stripped))
            is_list = bool(_LIST_RE.match(stripped))
            is_blockquote = bool(_BLOCKQUOTE_RE.match(stripped))

            if is_heading:
                result.append(stripped)
                prev_blank = False
                last_content_was_heading = True
                continue

            if is_list or is_blockquote:
                result.append(stripped)
                prev_blank = False
                last_content_was_heading = False
                continue

            # Normal paragraph text
            already_indented = line.startswith("\t") or line.startswith("    ")
            should_indent = (
                not last_content_was_heading  # First para after heading: no indent (APA)
                and not already_indented
                and prev_blank  # Only indent first line of new paragraphs
            )

            if should_indent:
                result.append(f"\t{stripped}")
                indent_count += 1
            else:
                result.append(stripped)

            prev_blank = False
            last_content_was_heading = False

        if indent_count:
            entries.append(
                self._entry(
                    "Sangría de primera línea aplicada a párrafos normales",
                    count=indent_count,
                )
            )

        return FixResult(text="\n".join(result), entries=entries)
