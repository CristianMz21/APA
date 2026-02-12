"""APA 7 document data models (Re-exported from Domain).

This module provides backward compatibility for existing code that imports from
`apa_formatter.models`. The actual definitions have moved to `apa_formatter.domain.models`.
"""

from apa_formatter.domain.models.document import (
    APADocument,
    Section,
    TitlePage,
)
from apa_formatter.domain.models.enums import (
    CitationType,
    FontChoice,
    HeadingLevel,
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
    "APADocument",
    "Author",
    "Citation",
    "CitationType",
    "FontChoice",
    "GroupAuthor",
    "HeadingLevel",
    "Reference",
    "ReferenceManager",
    "ReferenceType",
    "Section",
    "TitlePage",
]
