"""APA Preview widget — read-only QTextEdit for document preview."""

from __future__ import annotations

from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QTextEdit


class APAPreviewWidget(QTextEdit):
    """Read-only rich-text viewer that displays the APA-formatted document."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet(
            """
            APAPreviewWidget {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 24px;
            }
            """
        )

    def show_document(self, qt_doc: QTextDocument) -> None:
        """Replace the current content with the given QTextDocument."""
        self.setDocument(qt_doc)
