"""Per-fixer toggle panel for the auto-fix pipeline.

Allows power users to enable or disable individual fixers before running
the auto-correction pipeline.  Integrates as a collapsible section in the
``FixerReportPanel`` or as a standalone widget.

Usage::

    panel = FixerTogglePanel()
    enabled = panel.get_enabled_fixers()  # ['whitespace', 'character', …]
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.gui.theme import RADIUS_SM, SPACING_SM, Theme


# ---------------------------------------------------------------------------
# Fixer metadata
# ---------------------------------------------------------------------------

_FIXERS = [
    ("whitespace", "🔲 Espaciado", "Corrige espacios dobles, tabulaciones y líneas en blanco"),
    ("character", "🔤 Caracteres", "Reemplaza comillas tipográficas, guiones especiales, etc."),
    ("heading", "📑 Encabezados", "Detecta y normaliza niveles de encabezado (H1–H5)"),
    ("paragraph", "¶  Párrafos", "Aplica sangría, interlineado y estructura de párrafo"),
    ("citation", "📝 Citas", "Corrige formato de citas in-text (Author, Year)"),
    ("reference", "📚 Referencias", "Valida y ordena la lista de referencias APA"),
]


class FixerTogglePanel(QFrame):
    """Panel with per-fixer enable/disable checkboxes.

    Signals:
        config_changed: emitted when any checkbox state changes.
    """

    config_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("⚙️ Filtros de corrección")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Checkboxes
        self._checkboxes: dict[str, QCheckBox] = {}
        for fixer_id, label, tooltip in _FIXERS:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setToolTip(tooltip)
            cb.stateChanged.connect(lambda _: self.config_changed.emit())
            layout.addWidget(cb)
            self._checkboxes[fixer_id] = cb

        self._apply_style()

    # -- Public API ----------------------------------------------------------

    def get_enabled_fixers(self) -> list[str]:
        """Return list of enabled fixer IDs."""
        return [fixer_id for fixer_id, cb in self._checkboxes.items() if cb.isChecked()]

    def set_enabled_fixers(self, fixer_ids: list[str]) -> None:
        """Set which fixers are enabled."""
        for fixer_id, cb in self._checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(fixer_id in fixer_ids)
            cb.blockSignals(False)

    def all_enabled(self) -> bool:
        """Return True if all fixers are enabled."""
        return all(cb.isChecked() for cb in self._checkboxes.values())

    # -- Internal ------------------------------------------------------------

    def _apply_style(self) -> None:
        p = Theme.palette()
        self.setStyleSheet(f"""
            FixerTogglePanel {{
                background: {p.bg_secondary};
                border: 1px solid {p.border_light};
                border-radius: {RADIUS_SM};
            }}
            QCheckBox {{
                color: {p.text_primary};
                font-size: 9pt;
                spacing: {SPACING_SM};
                padding: 2px 0;
            }}
        """)

    def refresh_theme(self) -> None:
        """Re-apply theme after mode switch."""
        self._apply_style()
