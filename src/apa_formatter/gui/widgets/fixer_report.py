"""Grammarly-style fixer report panel.

Displays results from ``APAAutoFormatter.run()`` in a categorized card
layout.  Each ``FixCategory`` gets a collapsible section with individual
``FixEntry`` descriptions.

Usage::

    panel = FixerReportPanel()
    panel.show_result(fix_result)          # populate from FixResult
    panel.accepted.connect(on_user_accept) # user clicked "Accept All"
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.automation.base import FixCategory, FixEntry, FixResult
from apa_formatter.gui.theme import (
    RADIUS_SM,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL,
    Theme,
)


# ---------------------------------------------------------------------------
# Category display metadata
# ---------------------------------------------------------------------------

_CATEGORY_META: dict[FixCategory, tuple[str, str]] = {
    FixCategory.WHITESPACE: ("🔲", "Espaciado"),
    FixCategory.CHARACTER: ("🔤", "Caracteres"),
    FixCategory.HEADING: ("📑", "Encabezados"),
    FixCategory.PARAGRAPH: ("¶", "Párrafos"),
    FixCategory.CITATION: ("📝", "Citas"),
    FixCategory.REFERENCE: ("📚", "Referencias"),
}


# ---------------------------------------------------------------------------
# Fix entry card
# ---------------------------------------------------------------------------


class _FixCard(QFrame):
    """Single fix entry card with icon, message, and count badge."""

    def __init__(self, entry: FixEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        p = Theme.palette()

        self.setStyleSheet(
            f"QFrame {{ background: {p.bg_surface}; border: 1px solid {p.border_light}; "
            f"border-radius: {RADIUS_SM}; padding: {SPACING_SM}; }}"
            f"QFrame:hover {{ border-color: {p.accent}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Icon
        icon, _ = _CATEGORY_META.get(entry.category, ("•", "Otro"))
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(20)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        # Message
        msg_lbl = QLabel(entry.message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color: {p.text_primary}; font-size: 9pt; border: none; background: transparent;"
        )
        layout.addWidget(msg_lbl, stretch=1)

        # Count badge
        if entry.count > 1:
            badge = QLabel(f"×{entry.count}")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(32, 20)
            badge.setStyleSheet(
                f"background: {p.accent}; color: {p.text_inverse}; "
                f"border-radius: 10px; font-size: 8pt; font-weight: bold; border: none;"
            )
            layout.addWidget(badge)

        # Detail tooltip
        if entry.detail:
            self.setToolTip(entry.detail)


# ---------------------------------------------------------------------------
# Category section (collapsible header + cards)
# ---------------------------------------------------------------------------


class _CategorySection(QWidget):
    """Collapsible section for a single FixCategory."""

    def __init__(
        self,
        category: FixCategory,
        entries: list[FixEntry],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        p = Theme.palette()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(4)

        # Header
        icon, label_text = _CATEGORY_META.get(category, ("•", category.value))
        total = sum(e.count for e in entries)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(f"{icon}  {label_text}")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {p.text_primary};")
        header_layout.addWidget(title)

        count_lbl = QLabel(f"{total} corrección{'es' if total != 1 else ''}")
        count_lbl.setStyleSheet(f"color: {p.text_muted}; font-size: 9pt;")
        header_layout.addWidget(count_lbl)
        header_layout.addStretch()

        # Toggle button
        self._expanded = True
        self._toggle_btn = QPushButton("▼")
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {p.text_muted}; "
            "border: none; font-size: 10pt; }}"
            f"QPushButton:hover {{ color: {p.accent}; }}"
        )
        self._toggle_btn.clicked.connect(self._on_toggle)
        header_layout.addWidget(self._toggle_btn)

        layout.addWidget(header)

        # Cards container
        self._cards_container = QWidget()
        cards_layout = QVBoxLayout(self._cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(3)

        for entry in entries:
            cards_layout.addWidget(_FixCard(entry))

        layout.addWidget(self._cards_container)

    def _on_toggle(self) -> None:
        self._expanded = not self._expanded
        self._cards_container.setVisible(self._expanded)
        self._toggle_btn.setText("▼" if self._expanded else "▶")


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------


class FixerReportPanel(QWidget):
    """Grammarly-style panel showing auto-correction results.

    Signals:
        accepted: Emitted when the user clicks "Accept All".
        dismissed: Emitted when the user clicks "Dismiss".
    """

    accepted = Signal()
    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)

        self._result: FixResult | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────
        self._header = QWidget()
        header_layout = QVBoxLayout(self._header)
        header_layout.setContentsMargins(12, 10, 12, 8)

        self._title_label = QLabel("✨ Auto-correcciones APA")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        header_layout.addWidget(self._title_label)

        self._summary_label = QLabel("")
        header_layout.addWidget(self._summary_label)

        outer.addWidget(self._header)

        # ── Scroll area for cards ──────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setContentsMargins(12, 4, 12, 4)
        self._scroll_layout.setSpacing(8)
        self._scroll_layout.addStretch()
        self._scroll.setWidget(self._scroll_content)
        outer.addWidget(self._scroll, stretch=1)

        # ── Action buttons ─────────────────────────────────────────────
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(12, 8, 12, 10)

        self._accept_btn = QPushButton("✅ Aceptar Todo")
        self._accept_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(self._accept_btn)

        self._dismiss_btn = QPushButton("Descartar")
        self._dismiss_btn.clicked.connect(self._on_dismiss)
        btn_layout.addWidget(self._dismiss_btn)

        outer.addWidget(btn_row)

        # Initial style
        self._apply_style()

        # Empty state
        self._show_empty()

    # ── Public API ─────────────────────────────────────────────────────

    def show_result(self, result: FixResult) -> None:
        """Populate the panel from a ``FixResult``."""
        self._result = result
        self._clear_cards()

        if not result.entries:
            self._show_empty(message="✅ No se encontraron problemas — tu texto está limpio.")
            return

        # Group entries by category
        groups: dict[FixCategory, list[FixEntry]] = {}
        for entry in result.entries:
            groups.setdefault(entry.category, []).append(entry)

        # Category order: most entries first
        for cat in sorted(groups, key=lambda c: -sum(e.count for e in groups[c])):
            section = _CategorySection(cat, groups[cat])
            # Insert before the stretch
            self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, section)

        # Summary
        total = result.total_fixes
        cats = len(groups)
        self._summary_label.setText(
            f"{total} corrección{'es' if total != 1 else ''} en "
            f"{cats} categoría{'s' if cats != 1 else ''}"
        )
        p = Theme.palette()
        self._summary_label.setStyleSheet(f"color: {p.text_secondary}; font-size: 9pt;")

        self._accept_btn.setEnabled(True)

    def get_result(self) -> FixResult | None:
        """Return the current FixResult, if any."""
        return self._result

    # ── Internal ───────────────────────────────────────────────────────

    def _clear_cards(self) -> None:
        while self._scroll_layout.count() > 1:
            item = self._scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_empty(self, message: str = "Ejecuta Auto-corregir para ver resultados") -> None:
        self._accept_btn.setEnabled(False)
        p = Theme.palette()
        self._summary_label.setText(message)
        self._summary_label.setStyleSheet(
            f"color: {p.text_muted}; font-size: 9pt; font-style: italic;"
        )

    def _on_accept(self) -> None:
        self.accepted.emit()

    def _on_dismiss(self) -> None:
        self._result = None
        self._clear_cards()
        self._show_empty()
        self.dismissed.emit()

    def _apply_style(self) -> None:
        p = Theme.palette()
        self.setStyleSheet(f"""
            FixerReportPanel {{
                background: {p.bg_primary};
                border-left: 1px solid {p.border};
            }}
        """)
        self._header.setStyleSheet(f"""
            QWidget {{
                background: {p.bg_secondary};
                border-bottom: 1px solid {p.border};
            }}
        """)
        self._title_label.setStyleSheet(f"color: {p.text_primary}; background: transparent;")
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background: {p.bg_primary};
                border: none;
            }}
        """)
        self._accept_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p.success};
                color: {p.text_inverse};
                border: none;
                border-radius: {RADIUS_SM};
                padding: {SPACING_MD} {SPACING_XL};
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {p.accent_hover}; }}
            QPushButton:disabled {{ background: {p.border}; color: {p.text_muted}; }}
        """)
        self._dismiss_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {p.text_secondary};
                border: 1px solid {p.border};
                border-radius: {RADIUS_SM};
                padding: {SPACING_MD} {SPACING_XL};
                font-size: 10pt;
            }}
            QPushButton:hover {{ background: {p.bg_secondary}; }}
        """)

    def refresh_theme(self) -> None:
        """Re-apply styles after a theme change."""
        self._apply_style()
