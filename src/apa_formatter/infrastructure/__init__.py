"""Infrastructure layer — external framework adapters."""

from apa_formatter.infrastructure.renderers.docx_renderer import DocxRenderer
from apa_formatter.infrastructure.renderers.pdf_renderer import PdfRenderer
from apa_formatter.infrastructure.clipboard.system_clipboard import SystemClipboard
from apa_formatter.infrastructure.persistence.json_repository import JsonReferenceRepository
from apa_formatter.infrastructure.config.json_config_provider import JsonConfigProvider
from apa_formatter.infrastructure.checkers.docx_checker import DocxComplianceChecker
from apa_formatter.infrastructure.fetchers.doi_fetcher import DoiFetcher
from apa_formatter.infrastructure.fetchers.isbn_fetcher import IsbnFetcher
from apa_formatter.infrastructure.fetchers.url_fetcher import UrlFetcher

__all__ = [
    "DocxRenderer",
    "PdfRenderer",
    "SystemClipboard",
    "JsonReferenceRepository",
    "JsonConfigProvider",
    "DocxComplianceChecker",
    "DoiFetcher",
    "IsbnFetcher",
    "UrlFetcher",
]
