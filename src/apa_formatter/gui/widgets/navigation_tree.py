"""Document navigation tree — outline sidebar.

Displays the hierarchical structure of an ``APADocument`` as a clickable
tree.  Sections, appendices, abstract, and references are shown as nodes.
Clicking a node emits ``section_clicked`` with the section index so the
preview can scroll to it.

Usage::

    tree = NavigationTree()
    tree.set_document(apa_doc)
    tree.section_clicked.connect(lambda idx: preview.scroll_to(idx))
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.gui.theme import RADIUS_SM, SPACING_SM, Theme
from apa_formatter.models.document import APADocument, Section


# ---------------------------------------------------------------------------
# Heading level to indentation icons
# ---------------------------------------------------------------------------

_LEVEL_ICONS = {
    1: "📄",  # H1 — major section
    2: "  📑",  # H2
    3: "    📋",  # H3
    4: "      📌",  # H4
    5: "        •",  # H5
}


# ---------------------------------------------------------------------------
# Navigation Tree Widget
# ---------------------------------------------------------------------------


class NavigationTree(QWidget):
    """Sidebar tree showing document outline (TOC-style navigation).

    Signals:
        section_clicked(int): index of the section the user clicked.
        node_clicked(str): string label of the clicked node (for status bar).
    """

    section_clicked = Signal(int)
    node_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 6)

        title = QLabel("📑 Estructura del documento")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)

        layout.addWidget(header)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(16)
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree, stretch=1)

        # Empty state label
        self._empty_label = QLabel("Formatea un documento\npara ver su estructura")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        layout.addWidget(self._empty_label)

        self._apply_style()

    # -- Public API ----------------------------------------------------------

    def set_document(self, doc: APADocument) -> None:
        """Populate the tree from an APADocument."""
        self._tree.clear()
        self._empty_label.setVisible(False)
        self._tree.setVisible(True)

        section_index = 0

        # Title page (always present)
        title_item = QTreeWidgetItem(["📄 " + doc.title_page.title[:50]])
        title_item.setData(0, Qt.ItemDataRole.UserRole, -1)  # Not a section
        title_item.setFont(0, self._bold_font())
        self._tree.addTopLevelItem(title_item)

        # Abstract
        if doc.abstract:
            abs_item = QTreeWidgetItem(["📝 Resumen"])
            abs_item.setData(0, Qt.ItemDataRole.UserRole, -2)
            self._tree.addTopLevelItem(abs_item)

        # Sections
        for i, section in enumerate(doc.sections):
            item = self._build_section_item(section, section_index + i)
            self._tree.addTopLevelItem(item)

        section_index += len(doc.sections)

        # Appendices
        if doc.appendices:
            appendix_parent = QTreeWidgetItem(["📎 Apéndices"])
            appendix_parent.setData(0, Qt.ItemDataRole.UserRole, -3)
            appendix_parent.setFont(0, self._bold_font())
            for j, appendix in enumerate(doc.appendices):
                child = self._build_section_item(appendix, section_index + j)
                appendix_parent.addChild(child)
            self._tree.addTopLevelItem(appendix_parent)

        # References
        if doc.references:
            ref_item = QTreeWidgetItem([f"📚 Referencias ({len(doc.references)})"])
            ref_item.setData(0, Qt.ItemDataRole.UserRole, -4)
            self._tree.addTopLevelItem(ref_item)

        self._tree.expandAll()

    def clear(self) -> None:
        """Reset to empty state."""
        self._tree.clear()
        self._tree.setVisible(False)
        self._empty_label.setVisible(True)

    # -- Internal ------------------------------------------------------------

    def _build_section_item(self, section: Section, index: int) -> QTreeWidgetItem:
        """Recursively build tree items for a section and its subsections."""
        level = section.level.value if hasattr(section.level, "value") else 1
        icon = _LEVEL_ICONS.get(level, "•")
        heading = section.heading or f"Sección {index + 1}"
        label = f"{icon} {heading}"

        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, index)

        # Bold for top-level headings
        if level <= 2:
            item.setFont(0, self._bold_font())

        # Recursive subsections
        for sub in section.subsections:
            child = self._build_section_item(sub, index)
            item.addChild(child)

        return item

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        index = item.data(0, Qt.ItemDataRole.UserRole)
        label = item.text(0).strip()
        self.node_clicked.emit(label)
        if isinstance(index, int) and index >= 0:
            self.section_clicked.emit(index)

    def _bold_font(self) -> QFont:
        f = QFont()
        f.setBold(True)
        f.setPointSize(10)
        return f

    def _apply_style(self) -> None:
        p = Theme.palette()
        self.setStyleSheet(f"""
            NavigationTree {{
                background: {p.bg_primary};
                border-right: 1px solid {p.border};
            }}
        """)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {p.bg_primary};
                border: none;
                color: {p.text_primary};
                font-size: 9pt;
            }}
            QTreeWidget::item {{
                padding: {SPACING_SM} 4px;
                border-radius: {RADIUS_SM};
            }}
            QTreeWidget::item:hover {{
                background: {p.accent_subtle};
            }}
            QTreeWidget::item:selected {{
                background: {p.accent_subtle};
                color: {p.accent};
            }}
        """)
        self._empty_label.setStyleSheet(
            f"color: {p.text_muted}; font-size: 9pt; font-style: italic; padding: 20px;"
        )

    def refresh_theme(self) -> None:
        """Re-apply theme after mode switch."""
        self._apply_style()
