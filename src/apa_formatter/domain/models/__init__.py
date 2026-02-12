"""Domain models — public API.

Provides convenient imports for the most commonly used domain entities.
"""

from apa_formatter.domain.models.document import (
    APADocument,
    Section,
    TitlePage,
)
from apa_formatter.domain.models.enums import (
    CitationType,
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
    ReferenceType,
)
from apa_formatter.domain.models.reference import (
    Author,
    Citation,
    GroupAuthor,
    Reference,
)
from apa_formatter.domain.models.reference_manager import ReferenceManager

__all__ = [
    # Document
    "APADocument",
    "Section",
    "TitlePage",
    # Enums
    "CitationType",
    "DocumentVariant",
    "FontChoice",
    "HeadingLevel",
    "OutputFormat",
    "ReferenceType",
    # References
    "Author",
    "Citation",
    "GroupAuthor",
    "Reference",
    "ReferenceManager",
]
