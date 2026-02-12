"""GUI test suite for APA 7 Formatter.

Tests cover:
1. Theme system (light palette, stylesheet generation)
2. UserSettings persistence
3. Widget construction (preview, document form, import dialog)
4. Integration flows (build document → preview → stats)

Requires: pytest-qt, QT_QPA_PLATFORM=offscreen (set in conftest or env).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. Theme system tests (no Qt required)
# ---------------------------------------------------------------------------


class TestThemeSystem:
    """Tests for the centralized theme module."""

    def test_default_palette_is_light(self):
        from apa_formatter.gui.theme import Theme

        p = Theme.palette()
        assert p.bg_primary == "#FFFFFF"
        assert p.accent == "#4A6CF7"

    def test_palette_has_status_colors(self):
        from apa_formatter.gui.theme import Theme

        p = Theme.palette()
        assert p.success == "#27AE60"
        assert p.warning == "#F5A623"
        assert p.error == "#E74C3C"
        assert p.info == "#3498DB"

    def test_global_stylesheet_is_nonempty(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.global_stylesheet()
        assert "QMainWindow" in ss
        assert "QScrollBar" in ss
        assert len(ss) > 100

    def test_toolbar_stylesheet_contains_qtoolbar(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.toolbar()
        assert "QToolBar" in ss
        assert "QToolButton" in ss

    def test_tab_widget_stylesheet(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.tab_widget()
        assert "QTabBar" in ss
        assert "QTabWidget" in ss

    def test_form_inputs_stylesheet(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.form_inputs()
        assert "QLineEdit" in ss
        assert "QCheckBox" in ss

    def test_dialog_stylesheet_includes_components(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.dialog()
        assert "QDialog" in ss
        assert "QLineEdit" in ss
        assert "QPushButton" in ss

    def test_table_stylesheet(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.table()
        assert "QTableWidget" in ss
        assert "QHeaderView" in ss

    def test_splitter_stylesheet(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.splitter()
        assert "QSplitter" in ss

    def test_preview_panel_stylesheet(self):
        from apa_formatter.gui.theme import Theme

        ss = Theme.preview_panel()
        assert "QTextEdit" in ss

    def test_multiple_stylesheet_methods_return_content(self):
        from apa_formatter.gui.theme import Theme

        for method in [
            Theme.toolbar,
            Theme.tab_widget,
            Theme.form_inputs,
            Theme.group_box,
            Theme.button_primary,
            Theme.dialog,
            Theme.table,
            Theme.splitter,
            Theme.preview_panel,
        ]:
            ss = method()
            assert len(ss) > 10, f"{method.__name__} returned too short a stylesheet"


# ---------------------------------------------------------------------------
# 2. UserSettings tests (no Qt required)
# ---------------------------------------------------------------------------


class TestUserSettings:
    """Tests for the UserSettings model."""

    def test_default_dark_mode_is_false(self):
        from apa_formatter.domain.models.settings import UserSettings

        settings = UserSettings()
        assert settings.system.dark_mode is False

    def test_dark_mode_can_be_set(self):
        from apa_formatter.domain.models.settings import UserSettings

        settings = UserSettings()
        settings.system.dark_mode = True
        assert settings.system.dark_mode is True

    def test_serialization_roundtrip(self):
        from apa_formatter.domain.models.settings import UserSettings

        settings = UserSettings()
        settings.system.dark_mode = True

        data = settings.model_dump()
        restored = UserSettings(**data)
        assert restored.system.dark_mode is True


# ---------------------------------------------------------------------------
# 3. Widget construction tests (need QApplication)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for widget tests."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestAPAPreviewWidget:
    """Tests for the preview widget."""

    def test_construction(self, qapp):
        from apa_formatter.gui.widgets.preview import APAPreviewWidget

        widget = APAPreviewWidget()
        assert widget is not None

    def test_set_document_stats(self, qapp):
        from apa_formatter.gui.widgets.preview import APAPreviewWidget

        widget = APAPreviewWidget()
        widget.set_document_stats(word_count=500, section_count=3, ref_count=10, font_name="Arial")
        # Verify internal state
        assert widget._word_count == 500
        assert widget._section_count == 3
        assert widget._ref_count == 10
        assert widget._font_name == "Arial"

    def test_show_document(self, qapp):
        from PySide6.QtGui import QTextDocument
        from apa_formatter.gui.widgets.preview import APAPreviewWidget

        widget = APAPreviewWidget()
        doc = QTextDocument()
        doc.setPlainText("Hello APA World")
        widget.show_document(doc)
        assert widget._doc is doc

    def test_zoom_defaults(self, qapp):
        from apa_formatter.gui.widgets.preview import APAPreviewWidget

        widget = APAPreviewWidget()
        assert widget._zoom == 100  # default zoom


class TestDocumentFormWidget:
    """Tests for the document form widget."""

    def test_construction(self, qapp):
        from apa_formatter.gui.widgets.document_form import DocumentFormWidget

        widget = DocumentFormWidget()
        assert widget is not None

    def test_opciones_tab_defaults(self, qapp):
        from apa_formatter.gui.widgets.document_form import DocumentFormWidget

        widget = DocumentFormWidget()
        opts = widget._opciones.get_options()
        assert opts["margin_top_cm"] == 2.54
        assert opts["line_spacing"] == 2.0
        assert opts["include_toc"] is False
        assert opts["running_head"] is False
        assert opts["page_num_position"] == "Esquina superior derecha"

    def test_opciones_get_set_roundtrip(self, qapp):
        from apa_formatter.gui.widgets.document_form import DocumentFormWidget

        widget = DocumentFormWidget()
        widget._opciones.set_options(
            {
                "line_spacing": 1.5,
                "running_head": True,
                "font_name": "Arial",
                "page_size": "A4",
            }
        )
        opts = widget._opciones.get_options()
        assert opts["line_spacing"] == 1.5
        assert opts["running_head"] is True
        assert opts["font_name"] == "Arial"
        assert opts["page_size"] == "A4"

    def test_opciones_clear(self, qapp):
        from apa_formatter.gui.widgets.document_form import DocumentFormWidget

        widget = DocumentFormWidget()
        widget._opciones.set_options({"line_spacing": 1.5, "running_head": True})
        widget._opciones.clear()
        opts = widget._opciones.get_options()
        assert opts["line_spacing"] == 2.0
        assert opts["running_head"] is False


class TestImportDialog:
    """Tests for the import dialog."""

    def test_construction(self, qapp):
        from apa_formatter.gui.widgets.import_dialog import ImportDialog

        dlg = ImportDialog()
        assert dlg is not None
        assert dlg._result_doc is None

    def test_construction_with_filepath(self, qapp, tmp_path):
        from apa_formatter.gui.widgets.import_dialog import ImportDialog

        # Non-existent file won't trigger auto-analysis
        fake = tmp_path / "test.docx"
        dlg = ImportDialog(filepath=fake)
        assert dlg._initial_filepath == fake


# ---------------------------------------------------------------------------
# 4. Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests for the document pipeline."""

    def test_build_document_and_render(self, qapp):
        """Build an APADocument → render → show in preview."""
        from apa_formatter.models.document import APADocument, TitlePage, Section
        from apa_formatter.gui.rendering.apa_renderer import render_to_qtextdocument
        from apa_formatter.gui.widgets.preview import APAPreviewWidget

        doc = APADocument(
            title_page=TitlePage(
                title="Test Title",
                authors=["Author One"],
                affiliation="Test University",
            ),
            sections=[
                Section(title="Introduction", content="This is a test."),
                Section(title="Method", content="We tested things."),
            ],
        )

        qt_doc = render_to_qtextdocument(doc)
        assert qt_doc is not None

        widget = APAPreviewWidget()
        widget.show_document(qt_doc)
        widget.set_document_stats(word_count=12, section_count=2, ref_count=0)
        assert widget._doc is qt_doc
        assert widget._word_count == 12

    def test_opciones_set_from_config(self, qapp):
        """Test that OpcionesTab correctly loads from APAConfig."""
        from apa_formatter.config.loader import load_config
        from apa_formatter.gui.widgets.document_form import DocumentFormWidget

        config = load_config()
        widget = DocumentFormWidget()
        widget._opciones.set_from_config(config)

        opts = widget._opciones.get_options()
        assert opts["margin_top_cm"] == config.configuracion_pagina.margenes.superior_cm
        assert opts["line_spacing"] == config.formato_texto.interlineado_general

    def test_theme_apply_to_app(self, qapp):
        """Test that apply_theme doesn't crash."""
        from apa_formatter.gui.theme import apply_theme

        apply_theme(qapp)
        # If we get here without errors, the test passes
