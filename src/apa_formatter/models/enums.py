"""Enumerations for APA 7 document formatting."""

from enum import Enum


class HeadingLevel(int, Enum):
    """APA 7 heading levels (1-5)."""

    LEVEL_1 = 1  # Centered, Bold, Title Case
    LEVEL_2 = 2  # Flush Left, Bold, Title Case
    LEVEL_3 = 3  # Flush Left, Bold Italic, Title Case
    LEVEL_4 = 4  # Indented, Bold, Title Case, Period. Text continues...
    LEVEL_5 = 5  # Indented, Bold Italic, Title Case, Period. Text continues...


class FontChoice(str, Enum):
    """APA 7 approved fonts."""

    TIMES_NEW_ROMAN = "Times New Roman"
    CALIBRI = "Calibri"
    ARIAL = "Arial"
    GEORGIA = "Georgia"
    LUCIDA_SANS_UNICODE = "Lucida Sans Unicode"
    COMPUTER_MODERN = "Computer Modern"


class ReferenceType(str, Enum):
    """Types of APA 7 references."""

    BOOK = "book"
    EDITED_BOOK = "edited_book"
    BOOK_CHAPTER = "book_chapter"
    JOURNAL_ARTICLE = "journal_article"
    CONFERENCE_PAPER = "conference_paper"
    DISSERTATION = "dissertation"
    WEBPAGE = "webpage"
    REPORT = "report"
    NEWSPAPER = "newspaper"
    MAGAZINE = "magazine"
    SOFTWARE = "software"
    AUDIOVISUAL = "audiovisual"
    SOCIAL_MEDIA = "social_media"
    LEGAL = "legal"


class CitationType(str, Enum):
    """In-text citation styles."""

    PARENTHETICAL = "parenthetical"  # (Author, Year)
    NARRATIVE = "narrative"  # Author (Year)


class DocumentVariant(str, Enum):
    """APA 7 paper types."""

    STUDENT = "student"
    PROFESSIONAL = "professional"


class OutputFormat(str, Enum):
    """Output file formats."""

    DOCX = "docx"
    PDF = "pdf"
