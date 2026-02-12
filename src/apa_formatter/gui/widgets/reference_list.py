"""Reference list widget for managing all document references.

Provides a table view with Add/Edit/Delete buttons and auto-APA-sort.
Integrates with the DocumentFormWidget to inject references into the document.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.models.document import Reference
from apa_formatter.gui.widgets.reference_dialog import ReferenceDialog


class ReferenceListWidget(QWidget):
    """Table-based reference manager with CRUD buttons."""

    references_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._references: list[Reference] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Table ─────────────────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Autores", "Año", "Título", "Tipo"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self._table)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Agregar Referencia")
        btn_add.clicked.connect(self._on_add)
        btn_edit = QPushButton("✏️ Editar")
        btn_edit.clicked.connect(self._on_edit)
        btn_delete = QPushButton("🗑 Eliminar")
        btn_delete.clicked.connect(self._on_delete)
        btn_sort = QPushButton("🔤 Ordenar APA")
        btn_sort.setToolTip("Ordenar alfabéticamente por apellido del primer autor")
        btn_sort.clicked.connect(self._on_sort)

        btn_copy = QPushButton("📋 Copiar APA")
        btn_copy.setToolTip("Copiar la referencia seleccionada en formato APA")
        btn_copy.clicked.connect(self._on_copy)

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        btn_row.addWidget(btn_sort)
        layout.addLayout(btn_row)

        self.setStyleSheet(_LIST_STYLE)

    # ── Public API ────────────────────────────────────────────────────────

    def get_references(self) -> list[Reference]:
        return list(self._references)

    def set_references(self, refs: list[Reference]) -> None:
        self._references = list(refs)
        self._refresh_table()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        dlg = ReferenceDialog(self)
        if dlg.exec() == ReferenceDialog.DialogCode.Accepted:
            ref = dlg.get_reference()
            if ref:
                self._references.append(ref)
                self._refresh_table()
                self.references_changed.emit()

    def _on_edit(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._references):
            return
        dlg = ReferenceDialog(self, reference=self._references[row])
        if dlg.exec() == ReferenceDialog.DialogCode.Accepted:
            ref = dlg.get_reference()
            if ref:
                self._references[row] = ref
                self._refresh_table()
                self.references_changed.emit()

    def _on_delete(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._references):
            self._references.pop(row)
            self._refresh_table()
            self.references_changed.emit()

    def _on_sort(self) -> None:
        """Sort alphabetically by first author's last name (APA style)."""
        self._references.sort(key=lambda r: r.authors[0].last_name.lower() if r.authors else "")
        self._refresh_table()
        self.references_changed.emit()

    def _on_copy(self) -> None:
        """Copy the selected reference in APA format to the clipboard."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._references):
            return
        ref = self._references[row]
        formatted = ref.format_apa()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(formatted)

    # ── Internal ──────────────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._references))
        for i, ref in enumerate(self._references):
            author_str = ref.format_authors_apa() or "(sin autores)"
            year_str = str(ref.year) if ref.year else "n.d."

            self._table.setItem(i, 0, QTableWidgetItem(author_str))
            self._table.setItem(i, 1, QTableWidgetItem(year_str))
            self._table.setItem(i, 2, QTableWidgetItem(ref.title))
            self._table.setItem(i, 3, QTableWidgetItem(ref.ref_type.value))


# ── Stylesheet ────────────────────────────────────────────────────────────

_LIST_STYLE = """
QTableWidget {
    border: 1px solid #CCCCCC;
    font-size: 10pt;
    gridline-color: #EEEEEE;
}
QTableWidget::item:selected {
    background: #4A90D9;
    color: white;
}
QHeaderView::section {
    background: #F5F5F5;
    border: 1px solid #DDDDDD;
    padding: 4px;
    font-weight: bold;
    font-size: 9pt;
}
QPushButton {
    background: #4A90D9;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 5px 12px;
    font-size: 9pt;
}
QPushButton:hover {
    background: #357ABD;
}
"""
