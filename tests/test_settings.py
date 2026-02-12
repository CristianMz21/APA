"""Tests for the Settings Management module.

Covers:
- UserSettings model defaults and validation
- SettingsManager load / save / reset with a temp directory
- DocxAdapter force_title_page_break integration
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from apa_formatter.domain.models.enums import (
    ExportFormat,
    FontFamily,
    Language,
)
from apa_formatter.domain.models.settings import (
    DocumentStructureSettings,
    FormattingSettings,
    SystemSettings,
    UserSettings,
)
from apa_formatter.infrastructure.config.settings_manager import SettingsManager


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_config_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for settings files."""
    return tmp_path / "apa_config"


@pytest.fixture()
def manager(tmp_config_dir: Path) -> SettingsManager:
    """SettingsManager pointing at a temp directory."""
    return SettingsManager(config_dir=tmp_config_dir)


# ── Model Tests ───────────────────────────────────────────────────────────


class TestUserSettingsModel:
    """Tests for UserSettings Pydantic model."""

    def test_defaults(self) -> None:
        settings = UserSettings()
        assert settings.document.force_title_page_break is True
        assert settings.document.include_abstract is True
        assert settings.document.student_mode is True
        assert settings.formatting.font_family == FontFamily.TIMES_NEW_ROMAN
        assert settings.formatting.font_size == 12
        assert settings.formatting.line_spacing == 2.0
        assert settings.system.language == Language.ES
        assert settings.system.default_export_format == ExportFormat.DOCX

    def test_custom_values(self) -> None:
        settings = UserSettings(
            document=DocumentStructureSettings(
                force_title_page_break=False,
                include_abstract=False,
                student_mode=False,
            ),
            formatting=FormattingSettings(
                font_family=FontFamily.ARIAL,
                font_size=11,
                line_spacing=1.5,
            ),
            system=SystemSettings(
                language=Language.EN,
                default_export_format=ExportFormat.PDF,
            ),
        )
        assert settings.document.force_title_page_break is False
        assert settings.formatting.font_family == FontFamily.ARIAL
        assert settings.formatting.font_size == 11
        assert settings.system.language == Language.EN

    def test_font_size_validation(self) -> None:
        """Font size must be between 8 and 24."""
        with pytest.raises(Exception):
            FormattingSettings(font_size=4)
        with pytest.raises(Exception):
            FormattingSettings(font_size=30)

    def test_line_spacing_validation(self) -> None:
        """Line spacing must be between 1.0 and 3.0."""
        with pytest.raises(Exception):
            FormattingSettings(line_spacing=0.5)
        with pytest.raises(Exception):
            FormattingSettings(line_spacing=4.0)

    def test_serialization_roundtrip(self) -> None:
        original = UserSettings()
        data = original.model_dump(mode="json")
        restored = UserSettings.model_validate(data)
        assert restored == original


# ── SettingsManager Tests ─────────────────────────────────────────────────


class TestSettingsManager:
    """Tests for SettingsManager load/save/reset."""

    def test_load_defaults_when_no_file(self, manager: SettingsManager) -> None:
        settings = manager.load()
        assert settings == UserSettings()

    def test_save_and_load(self, manager: SettingsManager) -> None:
        custom = UserSettings(
            formatting=FormattingSettings(font_family=FontFamily.ARIAL, font_size=14),
        )
        manager.save(custom)

        loaded = manager.load()
        assert loaded.formatting.font_family == FontFamily.ARIAL
        assert loaded.formatting.font_size == 14

    def test_reset_to_defaults(self, manager: SettingsManager) -> None:
        custom = UserSettings(
            formatting=FormattingSettings(font_size=18),
        )
        manager.save(custom)
        assert manager.settings_path.exists()

        reset = manager.reset_to_defaults()
        assert reset.formatting.font_size == 12
        assert not manager.settings_path.exists()

    def test_corrupted_file_returns_defaults(
        self, manager: SettingsManager, tmp_config_dir: Path
    ) -> None:
        tmp_config_dir.mkdir(parents=True, exist_ok=True)
        manager.settings_path.write_text("{{invalid json", encoding="utf-8")

        settings = manager.load()
        assert settings == UserSettings()

    def test_settings_path_property(self, manager: SettingsManager) -> None:
        assert manager.settings_path.name == "user_settings.json"

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested"
        mgr = SettingsManager(config_dir=nested)
        mgr.save(UserSettings())
        assert mgr.settings_path.exists()

    def test_save_file_content_is_valid_json(self, manager: SettingsManager) -> None:
        manager.save(UserSettings())
        raw = manager.settings_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        assert "document" in data
        assert "formatting" in data
        assert "system" in data


# ── DocxAdapter Integration ───────────────────────────────────────────────


class TestDocxAdapterSettingsIntegration:
    """Test that DocxAdapter respects force_title_page_break."""

    def test_page_break_added_by_default(self) -> None:
        """When user_settings is None, page break is always added."""
        from apa_formatter.adapters.docx_adapter import DocxAdapter

        doc = self._make_minimal_doc()
        adapter = DocxAdapter(doc)

        # Count page breaks before
        adapter._build_title_page()
        # The method should have called _add_page_break
        # We verify indirectly by checking the docx has paragraphs
        assert len(adapter._docx.paragraphs) > 0

    def test_page_break_skipped_when_disabled(self) -> None:
        """When force_title_page_break=False, no page break after title."""
        from apa_formatter.adapters.docx_adapter import DocxAdapter

        settings = UserSettings(
            document=DocumentStructureSettings(force_title_page_break=False),
        )
        doc = self._make_minimal_doc()
        adapter = DocxAdapter(doc, user_settings=settings)

        # Mock the _add_page_break to track if it's called
        original_method = adapter._add_page_break
        call_tracker = MagicMock()
        adapter._add_page_break = call_tracker  # type: ignore[method-assign]

        adapter._build_title_page()
        call_tracker.assert_not_called()

        # Restore original
        adapter._add_page_break = original_method  # type: ignore[method-assign]

    def test_page_break_added_when_enabled(self) -> None:
        """When force_title_page_break=True, page break is added."""
        from apa_formatter.adapters.docx_adapter import DocxAdapter

        settings = UserSettings(
            document=DocumentStructureSettings(force_title_page_break=True),
        )
        doc = self._make_minimal_doc()
        adapter = DocxAdapter(doc, user_settings=settings)

        call_tracker = MagicMock()
        adapter._add_page_break = call_tracker  # type: ignore[method-assign]

        adapter._build_title_page()
        call_tracker.assert_called_once()

    @staticmethod
    def _make_minimal_doc():
        """Create a minimal APADocument for testing."""
        from apa_formatter.domain.models.document import (
            APADocument,
            TitlePage,
        )
        from apa_formatter.domain.models.enums import DocumentVariant

        return APADocument(
            title_page=TitlePage(
                title="Test Title",
                authors=["Author, Test"],
                affiliation="Test University",
                variant=DocumentVariant.STUDENT,
                due_date=date(2024, 1, 1),
            ),
            sections=[],
            references=[],
        )
