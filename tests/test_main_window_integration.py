"""Integration tests for APAMainWindow."""

import pytest
from unittest.mock import MagicMock, patch
import os
from PySide6.QtCore import Qt

# Ensure offscreen platform
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication for widget tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    """Create a fresh APAMainWindow for each test."""
    from apa_formatter.gui.main_window import APAMainWindow

    window = APAMainWindow()
    yield window
    window.close()


def test_construction(main_window):
    """Test that the main window constructs correctly."""
    assert main_window.windowTitle() == "APA 7 Formatter"
    assert main_window.centralWidget() is not None


def test_export_docx_flow(main_window):
    """Test the DOCX export flow with mocks."""
    # Mock current doc exists
    main_window._current_doc = MagicMock()

    # Patch QFileDialog in PySide6.QtWidgets
    with patch(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        return_value=("test.docx", "Word Documents (*.docx)"),
    ) as mock_save:
        # Patch DocxAdapter where it is defined (since it is imported locally)
        with patch("apa_formatter.adapters.docx_adapter.DocxAdapter") as MockAdapter:
            mock_instance = MockAdapter.return_value

            # Helper to bypass potential QMessageBox confirms or allow defaults
            with patch.object(main_window, "_run_export_guard", return_value=True):
                # Force AI check to False
                with patch.object(main_window, "_ask_ai_correction", return_value=False):
                    main_window._on_export_docx()

            # Verify save dialog called
            mock_save.assert_called_once()

            # Verify adapter generated
            mock_instance.generate.assert_called_once()


def test_ai_correction_flow(main_window):
    """Test the AI correction flow during export."""
    main_window._current_doc = MagicMock()

    with patch(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName",
        return_value=("test_ai.docx", "Word Documents (*.docx)"),
    ):
        with patch.object(main_window, "_run_export_guard", return_value=True):
            # Mock AI check to confirm "Yes"
            with patch.object(main_window, "_ask_ai_correction", return_value=True):
                # Mock _run_ai_correction to invoke callback
                with patch.object(main_window, "_run_ai_correction") as mock_run_ai:

                    def side_effect(on_done):
                        # Invoke callback immediately
                        on_done()

                    mock_run_ai.side_effect = side_effect

                    # Mock DocxAdapter
                    with patch("apa_formatter.adapters.docx_adapter.DocxAdapter") as MockAdapter:
                        main_window._on_export_docx()

                        # Verify AI was requested
                        mock_run_ai.assert_called_once()
                        # Verify adapter validation/generation occurred (triggered by callback)
                        MockAdapter.return_value.generate.assert_called()


def test_auto_fix_flow(main_window):
    """Test the Auto-Fix (Reglas) flow."""
    # Mock sections data in form (UserRole dict)
    section_data = {"content": "Title in lowercase"}
    mock_item = MagicMock()
    mock_item.data.return_value = section_data

    # Mock the sections list widget
    main_window.form = MagicMock()
    main_window.form._sections_list.count.return_value = 1
    main_window.form._sections_list.item.return_value = mock_item

    # Mock imports inside the method

    with patch("apa_formatter.automation.pipeline.APAAutoFormatter") as MockFormatter:
        with patch("apa_formatter.gui.widgets.async_overlay.AsyncWorker") as MockWorker:
            with patch("apa_formatter.gui.widgets.async_overlay.AsyncOverlay") as MockOverlay:
                # Setup formatter mock
                mock_pipeline = MockFormatter.return_value

                # Setup worker mock
                mock_worker = MockWorker.return_value
                mock_worker.finished = MagicMock()
                mock_worker.error = MagicMock()

                # Trigger action (Step 1: Start)
                main_window._on_auto_fix()

                # Verify worker started
                MockWorker.assert_called()
                MockOverlay.return_value.run.assert_called_with(mock_worker)

                # Simulate completion (Step 2: Done)
                # Create a mock FixResult
                from apa_formatter.automation.base import FixResult

                mock_result = MagicMock(spec=FixResult)
                mock_result.text = "Title In Title Case"  # Correct attribute per code inspection
                mock_result.total_fixes = 5

                # Mock main_window.fixer_panel
                main_window.fixer_panel = MagicMock()
                main_window.fixer_panel.get_result.return_value = mock_result

                # Call _on_auto_fix_done
                main_window._on_auto_fix_done(mock_result)

                # Verify panel was shown
                main_window.fixer_panel.show_result.assert_called_with(mock_result)
                main_window.fixer_panel.setVisible.assert_called_with(True)

                # Simulate User Acceptance (Step 3: Accept)
                main_window._on_auto_fix_accept()

                # Verify data was updated
                # The code updates 'section_data' in place or calls setData
                # item.setData is called with updated data
                assert mock_item.setData.called
                args = mock_item.setData.call_args[0]
                assert args[1]["content"] == "Title In Title Case"
