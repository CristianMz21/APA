"""Composition Root — Dependency Injection Container.

This module is the ONLY place where concrete infrastructure classes are
imported and wired together.  All other layers refer to ports (interfaces).
"""

from __future__ import annotations

from typing import Any

from apa_formatter.domain.models.enums import OutputFormat
from apa_formatter.domain.ports.clipboard_port import ClipboardPort
from apa_formatter.domain.ports.compliance_checker import ComplianceCheckerPort
from apa_formatter.domain.ports.config_provider import ConfigProviderPort
from apa_formatter.domain.ports.document_renderer import DocumentRendererPort
from apa_formatter.domain.ports.metadata_fetcher import MetadataFetcherPort
from apa_formatter.domain.ports.reference_repository import ReferenceRepositoryPort

from apa_formatter.infrastructure.checkers.docx_checker import DocxComplianceChecker
from apa_formatter.infrastructure.clipboard.system_clipboard import SystemClipboard
from apa_formatter.infrastructure.config.json_config_provider import JsonConfigProvider
from apa_formatter.infrastructure.config.settings_manager import SettingsManager
from apa_formatter.infrastructure.fetchers.doi_fetcher import DoiFetcher
from apa_formatter.infrastructure.fetchers.isbn_fetcher import IsbnFetcher
from apa_formatter.infrastructure.fetchers.url_fetcher import UrlFetcher
from apa_formatter.infrastructure.persistence.json_repository import JsonReferenceRepository
from apa_formatter.infrastructure.renderers.docx_renderer import DocxRenderer
from apa_formatter.infrastructure.renderers.pdf_renderer import PdfRenderer

from apa_formatter.application.use_cases.check_compliance import CheckComplianceUseCase
from apa_formatter.application.use_cases.convert_document import ConvertDocumentUseCase
from apa_formatter.application.use_cases.copy_reference import CopyReferenceUseCase
from apa_formatter.application.use_cases.create_document import CreateDocumentUseCase
from apa_formatter.application.use_cases.fetch_metadata import FetchMetadataUseCase
from apa_formatter.application.use_cases.generate_demo import GenerateDemoUseCase
from apa_formatter.application.use_cases.manage_references import ManageReferencesUseCase

# Optional AI import (graceful when google-genai not installed)
try:
    from apa_formatter.infrastructure.ai.gemini_client import GeminiClient as _GeminiClient

    _HAS_AI = True
except ImportError:
    _HAS_AI = False


class Container:
    """Simple dependency injection container.

    Wires all infrastructure implementations to domain ports
    and provides pre-configured use cases.

    Usage::

        container = Container()
        uc = container.create_document(OutputFormat.DOCX)
        path = uc.execute(doc, Path("output.docx"))
    """

    def __init__(self, config_path: str | None = None) -> None:
        # -- Infrastructure singletons ---------------------------------------
        self._config_provider = JsonConfigProvider(config_path)
        self._config: Any = self._config_provider.get_config()

        self._docx_renderer = DocxRenderer(config=self._config)
        self._pdf_renderer = PdfRenderer(config=self._config)

        self._repository = JsonReferenceRepository()
        self._clipboard = SystemClipboard()
        self._compliance_checker = DocxComplianceChecker()

        self._doi_fetcher = DoiFetcher()
        self._isbn_fetcher = IsbnFetcher()
        self._url_fetcher = UrlFetcher()

        self._settings_manager = SettingsManager()

        # Optional AI client
        self._gemini_client: object | None = None
        if _HAS_AI:
            try:
                self._gemini_client = _GeminiClient()
            except Exception:
                pass  # No API key or other config issue — AI unavailable

    # -- Port accessors ------------------------------------------------------

    @property
    def config_provider(self) -> ConfigProviderPort:
        return self._config_provider

    @property
    def config(self) -> Any:
        return self._config

    @property
    def clipboard(self) -> ClipboardPort:
        return self._clipboard

    @property
    def repository(self) -> ReferenceRepositoryPort:
        return self._repository

    @property
    def compliance_checker(self) -> ComplianceCheckerPort:
        return self._compliance_checker

    @property
    def settings_manager(self) -> SettingsManager:
        return self._settings_manager

    @property
    def user_settings(self) -> Any:
        return self._settings_manager.load()

    def get_renderer(self, fmt: OutputFormat) -> DocumentRendererPort:
        """Return the renderer for the given output format."""
        if fmt == OutputFormat.PDF:
            return self._pdf_renderer
        return self._docx_renderer

    def get_fetcher(self, kind: str = "doi") -> MetadataFetcherPort:
        """Return a metadata fetcher by kind ('doi', 'isbn', 'url')."""
        fetchers = {
            "doi": self._doi_fetcher,
            "isbn": self._isbn_fetcher,
            "url": self._url_fetcher,
        }
        return fetchers.get(kind, self._doi_fetcher)

    # -- Use Case factories --------------------------------------------------

    def create_document(self, fmt: OutputFormat) -> CreateDocumentUseCase:
        """Create a use case for document creation."""
        return CreateDocumentUseCase(renderer=self.get_renderer(fmt))

    def generate_demo(self) -> GenerateDemoUseCase:
        """Create a use case for demo document generation."""
        return GenerateDemoUseCase()

    def convert_document(self, target_fmt: OutputFormat) -> ConvertDocumentUseCase:
        """Create a use case for format conversion."""
        return ConvertDocumentUseCase(target_renderer=self.get_renderer(target_fmt))

    def check_compliance(self) -> CheckComplianceUseCase:
        """Create a use case for compliance checking."""
        return CheckComplianceUseCase(checker=self._compliance_checker)

    def copy_reference(self) -> CopyReferenceUseCase:
        """Create a use case for copying references to clipboard."""
        return CopyReferenceUseCase(clipboard=self._clipboard)

    def manage_references(self) -> ManageReferencesUseCase:
        """Create a use case for reference CRUD operations."""
        return ManageReferencesUseCase(repository=self._repository)

    def fetch_metadata(self, kind: str = "doi") -> FetchMetadataUseCase:
        """Create a use case for metadata fetching."""
        return FetchMetadataUseCase(fetcher=self.get_fetcher(kind))

    # -- AI-powered import ---------------------------------------------------

    @property
    def has_ai(self) -> bool:
        """True if Gemini AI integration is available."""
        return self._gemini_client is not None

    @property
    def gemini_client(self) -> object | None:
        """Return the Gemini client (or None if unavailable)."""
        return self._gemini_client
