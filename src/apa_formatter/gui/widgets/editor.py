"""Editor widget — text input panel with placeholder."""

from __future__ import annotations

from PySide6.QtWidgets import QTextEdit


class EditorWidget(QTextEdit):
    """Multi-line text editor for raw content input."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(
            "Escribe o pega tu texto aquí...\n\n"
            "Cada párrafo se convertirá en una sección del documento APA."
        )
        self.setStyleSheet(
            """
            EditorWidget {
                background-color: #FAFAFA;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 12px;
                font-family: 'Monospace';
                font-size: 11pt;
            }
            """
        )
