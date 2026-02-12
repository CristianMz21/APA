"""Abstract base adapter for document output."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from apa_formatter.config import APAConfig, get_config
from apa_formatter.models.document import APADocument


class BaseAdapter(ABC):
    """Base class for document format adapters."""

    def __init__(self, document: APADocument, config: Optional[APAConfig] = None) -> None:
        self.doc = document
        self._config = config or get_config()

    @abstractmethod
    def generate(self, output_path: Path) -> Path:
        """Generate the formatted document and return the output path."""
        ...

    def _get_font_spec(self):
        """Get the font specification for the document's font choice."""
        from apa_formatter.rules.constants import FONT_SPECS

        return FONT_SPECS[self.doc.font]
