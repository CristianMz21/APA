"""Individual APA fixers — each corrects one category of issues."""

from apa_formatter.automation.fixers.character_fixer import CharacterFixer
from apa_formatter.automation.fixers.citation_fixer import CitationFixer
from apa_formatter.automation.fixers.heading_detector import HeadingDetector
from apa_formatter.automation.fixers.paragraph_fixer import ParagraphFixer
from apa_formatter.automation.fixers.reference_list_fixer import ReferenceListFixer
from apa_formatter.automation.fixers.whitespace_fixer import WhitespaceFixer

__all__ = [
    "CharacterFixer",
    "CitationFixer",
    "HeadingDetector",
    "ParagraphFixer",
    "ReferenceListFixer",
    "WhitespaceFixer",
]
