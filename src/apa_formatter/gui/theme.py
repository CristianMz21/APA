"""APA 7 Formatter — Centralized Design System.

Provides a single source of truth for all visual tokens: colors, fonts,
spacing, shadows, border radii, and component-level stylesheets.

Usage::

    from apa_formatter.gui.theme import Theme, apply_theme

    apply_theme(app)                       # apply to entire QApplication
    widget.setStyleSheet(Theme.TOOLBAR)    # component-specific stylesheet
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _Palette:
    """Color tokens for the light theme."""

    # Surface
    bg_primary: str
    bg_secondary: str
    bg_surface: str
    bg_elevated: str

    # Text
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverse: str

    # Accent
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_subtle: str

    # Status
    success: str
    warning: str
    error: str
    info: str

    # Borders
    border: str
    border_light: str
    border_focus: str

    # Shadow
    shadow: str


_LIGHT = _Palette(
    bg_primary="#FFFFFF",
    bg_secondary="#F5F6F8",
    bg_surface="#FFFFFF",
    bg_elevated="#FFFFFF",
    text_primary="#1A1A2E",
    text_secondary="#4A4A5A",
    text_muted="#8888A0",
    text_inverse="#FFFFFF",
    accent="#4A6CF7",
    accent_hover="#3B5CE4",
    accent_pressed="#2D4BC8",
    accent_subtle="#EEF0FF",
    success="#27AE60",
    warning="#F5A623",
    error="#E74C3C",
    info="#3498DB",
    border="#D8DCE6",
    border_light="#E8ECF4",
    border_focus="#4A6CF7",
    shadow="rgba(0, 0, 0, 0.08)",
)


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

FONT_FAMILY = "'Inter', 'Segoe UI', 'Roboto', system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"

RADIUS_SM = "3px"
RADIUS_MD = "6px"
RADIUS_LG = "10px"
RADIUS_XL = "14px"

SPACING_XS = "2px"
SPACING_SM = "4px"
SPACING_MD = "8px"
SPACING_LG = "12px"
SPACING_XL = "16px"
SPACING_2XL = "24px"


# ---------------------------------------------------------------------------
# Theme class — generates all stylesheets from palette
# ---------------------------------------------------------------------------


class Theme:
    """Generates Qt stylesheets from the light palette."""

    _palette: _Palette = _LIGHT

    @classmethod
    def palette(cls) -> _Palette:
        return cls._palette

    # ── Global application stylesheet ───────────────────────────────────

    @classmethod
    def global_stylesheet(cls) -> str:
        p = cls._palette
        return f"""
        * {{
            font-family: {FONT_FAMILY};
        }}

        QMainWindow, QDialog {{
            background: {p.bg_primary};
        }}

        QWidget {{
            color: {p.text_primary};
        }}

        QMenuBar {{
            background: {p.bg_secondary};
            color: {p.text_primary};
            border-bottom: 1px solid {p.border};
            padding: {SPACING_SM};
            font-size: 10pt;
        }}
        QMenuBar::item {{
            padding: {SPACING_SM} {SPACING_MD};
            border-radius: {RADIUS_SM};
        }}
        QMenuBar::item:selected {{
            background: {p.accent_subtle};
            color: {p.accent};
        }}

        QMenu {{
            background: {p.bg_elevated};
            border: 1px solid {p.border};
            border-radius: {RADIUS_MD};
            padding: {SPACING_SM};
        }}
        QMenu::item {{
            padding: {SPACING_SM} {SPACING_XL};
            border-radius: {RADIUS_SM};
        }}
        QMenu::item:selected {{
            background: {p.accent_subtle};
            color: {p.accent};
        }}

        QStatusBar {{
            background: {p.bg_secondary};
            color: {p.text_secondary};
            border-top: 1px solid {p.border};
            font-size: 9pt;
            padding: {SPACING_SM};
        }}

        QToolTip {{
            background: {p.bg_elevated};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: {RADIUS_SM};
            padding: {SPACING_SM} {SPACING_MD};
            font-size: 9pt;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {p.border};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {p.text_muted};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
        }}
        QScrollBar::handle:horizontal {{
            background: {p.border};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {p.text_muted};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        """

    # ── Component-level stylesheets ─────────────────────────────────────

    @classmethod
    def toolbar(cls) -> str:
        p = cls._palette
        return f"""
        QToolBar {{
            background: {p.bg_secondary};
            border-bottom: 1px solid {p.border};
            padding: {SPACING_SM} {SPACING_MD};
            spacing: {SPACING_SM};
        }}
        QToolBar QToolButton {{
            background: transparent;
            color: {p.text_primary};
            border: none;
            border-radius: {RADIUS_SM};
            padding: {SPACING_SM} {SPACING_MD};
            font-size: 10pt;
        }}
        QToolBar QToolButton:hover {{
            background: {p.accent_subtle};
            color: {p.accent};
        }}
        QToolBar QToolButton:pressed {{
            background: {p.accent};
            color: {p.text_inverse};
        }}
        QToolBar QToolButton:disabled {{
            color: {p.text_muted};
        }}
        QToolBar QComboBox {{
            background: {p.bg_surface};
            border: 1px solid {p.border};
            border-radius: {RADIUS_SM};
            padding: {SPACING_SM} {SPACING_MD};
            color: {p.text_primary};
            font-size: 9pt;
            min-width: 100px;
        }}
        QToolBar QComboBox:focus {{
            border-color: {p.border_focus};
        }}
        QToolBar QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QToolBar QComboBox QAbstractItemView {{
            background: {p.bg_elevated};
            border: 1px solid {p.border};
            selection-background-color: {p.accent_subtle};
            selection-color: {p.accent};
        }}
        """

    @classmethod
    def tab_widget(cls) -> str:
        p = cls._palette
        return f"""
        QTabWidget::pane {{
            background: {p.bg_surface};
            border: 1px solid {p.border};
            border-top: none;
            border-radius: 0 0 {RADIUS_MD} {RADIUS_MD};
        }}
        QTabBar::tab {{
            background: {p.bg_secondary};
            color: {p.text_secondary};
            border: 1px solid {p.border};
            border-bottom: none;
            padding: {SPACING_MD} {SPACING_XL};
            margin-right: 1px;
            font-size: 10pt;
            border-radius: {RADIUS_MD} {RADIUS_MD} 0 0;
        }}
        QTabBar::tab:selected {{
            background: {p.bg_surface};
            color: {p.accent};
            font-weight: bold;
            border-bottom: 2px solid {p.accent};
        }}
        QTabBar::tab:hover:!selected {{
            background: {p.accent_subtle};
            color: {p.text_primary};
        }}
        """

    @classmethod
    def form_inputs(cls) -> str:
        p = cls._palette
        return f"""
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background: {p.bg_surface};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: {RADIUS_SM};
            padding: {SPACING_SM} {SPACING_MD};
            font-size: 10pt;
            selection-background-color: {p.accent};
            selection-color: {p.text_inverse};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {p.border_focus};
        }}
        QLineEdit:disabled, QTextEdit:disabled {{
            background: {p.bg_secondary};
            color: {p.text_muted};
        }}
        QLabel {{
            color: {p.text_secondary};
            font-size: 10pt;
        }}
        QCheckBox {{
            color: {p.text_primary};
            font-size: 10pt;
            spacing: {SPACING_MD};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {p.border};
            border-radius: {RADIUS_SM};
            background: {p.bg_surface};
        }}
        QCheckBox::indicator:checked {{
            background: {p.accent};
            border-color: {p.accent};
        }}
        QComboBox {{
            background: {p.bg_surface};
            color: {p.text_primary};
            border: 1px solid {p.border};
            border-radius: {RADIUS_SM};
            padding: {SPACING_SM} {SPACING_MD};
            font-size: 10pt;
        }}
        QComboBox:focus {{
            border-color: {p.border_focus};
        }}
        """

    @classmethod
    def group_box(cls) -> str:
        p = cls._palette
        return f"""
        QGroupBox {{
            background: {p.bg_surface};
            border: 1px solid {p.border_light};
            border-radius: {RADIUS_MD};
            margin-top: 12px;
            padding-top: 16px;
            font-weight: bold;
            font-size: 10pt;
            color: {p.text_primary};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 {SPACING_MD};
            color: {p.accent};
        }}
        """

    @classmethod
    def button_primary(cls) -> str:
        p = cls._palette
        return f"""
        QPushButton {{
            background: {p.accent};
            color: {p.text_inverse};
            border: none;
            border-radius: {RADIUS_SM};
            padding: {SPACING_MD} {SPACING_XL};
            font-size: 10pt;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {p.accent_hover};
        }}
        QPushButton:pressed {{
            background: {p.accent_pressed};
        }}
        QPushButton:disabled {{
            background: {p.border};
            color: {p.text_muted};
        }}
        """

    @classmethod
    def dialog(cls) -> str:
        p = cls._palette
        return f"""
        QDialog {{
            background: {p.bg_primary};
        }}
        {cls.form_inputs()}
        {cls.group_box()}
        {cls.button_primary()}
        """

    @classmethod
    def table(cls) -> str:
        p = cls._palette
        return f"""
        QTableWidget, QTreeWidget {{
            background: {p.bg_surface};
            border: 1px solid {p.border_light};
            border-radius: {RADIUS_SM};
            gridline-color: {p.border_light};
            color: {p.text_primary};
            font-size: 9pt;
        }}
        QTableWidget::item, QTreeWidget::item {{
            padding: {SPACING_SM} {SPACING_MD};
        }}
        QTableWidget::item:selected, QTreeWidget::item:selected {{
            background: {p.accent_subtle};
            color: {p.accent};
        }}
        QHeaderView::section {{
            background: {p.bg_secondary};
            color: {p.text_secondary};
            border: none;
            border-bottom: 1px solid {p.border};
            padding: {SPACING_SM} {SPACING_MD};
            font-size: 9pt;
            font-weight: bold;
        }}
        """

    @classmethod
    def splitter(cls) -> str:
        p = cls._palette
        return f"""
        QSplitter::handle {{
            background: {p.border_light};
            width: 2px;
        }}
        QSplitter::handle:hover {{
            background: {p.accent};
        }}
        """

    @classmethod
    def preview_panel(cls) -> str:
        p = cls._palette
        return f"""
        QTextEdit {{
            background: {p.bg_secondary};
            selection-background-color: {p.accent};
            selection-color: {p.text_inverse};
            border: none;
        }}
        """


# ---------------------------------------------------------------------------
# Application-level helper
# ---------------------------------------------------------------------------


def apply_theme(app) -> None:
    """Apply the global theme stylesheet to a QApplication instance."""
    app.setStyleSheet(Theme.global_stylesheet())
