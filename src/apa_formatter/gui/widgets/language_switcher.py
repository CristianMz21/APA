"""Language switcher toolbar widget.

Provides a compact ``QComboBox`` for selecting the application language
(English / Español) and persists the choice via ``UserSettings``.

Usage::

    switcher = LanguageSwitcher()
    switcher.language_changed.connect(on_lang_changed)
    toolbar.addWidget(switcher)
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget


# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------

_LANGUAGES = [
    ("es", "🇪🇸 Español"),
    ("en", "🇺🇸 English"),
]


class LanguageSwitcher(QWidget):
    """Toolbar widget for switching application language.

    Signals:
        language_changed(str): emitted with the language code ('en' or 'es').
    """

    language_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        label = QLabel("🌐")
        label.setToolTip("Idioma de la interfaz")
        label.setStyleSheet("font-size: 12pt; padding: 0;")
        layout.addWidget(label)

        self._combo = QComboBox()
        self._combo.setToolTip("Seleccionar idioma")
        for code, display in _LANGUAGES:
            self._combo.addItem(display, code)
        self._combo.currentIndexChanged.connect(self._on_changed)
        layout.addWidget(self._combo)

    # -- Public API ----------------------------------------------------------

    def set_language(self, code: str) -> None:
        """Set the active language without emitting a signal."""
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == code:
                self._combo.blockSignals(True)
                self._combo.setCurrentIndex(i)
                self._combo.blockSignals(False)
                return

    def current_language(self) -> str:
        """Return the current language code."""
        return self._combo.currentData() or "es"

    # -- Internal ------------------------------------------------------------

    def _on_changed(self, _index: int) -> None:
        code = self._combo.currentData()
        if code:
            self.language_changed.emit(code)
