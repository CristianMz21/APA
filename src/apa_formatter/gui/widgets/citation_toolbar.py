"""Citation insertion toolbar for the section content editor.

Provides quick insertion of in-text citations (parenthetical and narrative)
based on references already added to the document.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from apa_formatter.models.document import Citation, Reference
from apa_formatter.models.enums import CitationType


class CitationToolbar(QWidget):
    """Compact toolbar for inserting in-text citations."""

    # Emitted with the formatted citation text to insert
    citation_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._references: list[Reference] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        layout.addWidget(QLabel("📌 Citar:"))

        self._ref_combo = QComboBox()
        self._ref_combo.setMinimumWidth(250)
        self._ref_combo.setPlaceholderText("Seleccionar referencia…")
        layout.addWidget(self._ref_combo, stretch=1)

        btn_paren = QPushButton("(Autor, Año)")
        btn_paren.setToolTip("Cita parentética — (García, 2023)")
        btn_paren.clicked.connect(self._insert_parenthetical)
        layout.addWidget(btn_paren)

        btn_narrative = QPushButton("Autor (Año)")
        btn_narrative.setToolTip("Cita narrativa — García (2023)")
        btn_narrative.clicked.connect(self._insert_narrative)
        layout.addWidget(btn_narrative)

        btn_page = QPushButton("+ p./pp.")
        btn_page.setToolTip("Cita parentética con número de página")
        btn_page.clicked.connect(self._insert_with_page)
        layout.addWidget(btn_page)

        self.setStyleSheet(_TOOLBAR_STYLE)

    def set_references(self, refs: list[Reference]) -> None:
        """Update the combo box with available references."""
        self._references = list(refs)
        self._ref_combo.clear()
        for ref in self._references:
            author_str = ref.format_authors_apa() if ref.authors else "(sin autor)"
            year_str = str(ref.year) if ref.year else "n.d."
            self._ref_combo.addItem(f"{author_str} ({year_str})")

    def _get_selected(self) -> Reference | None:
        idx = self._ref_combo.currentIndex()
        if 0 <= idx < len(self._references):
            return self._references[idx]
        return None

    def _build_citation(self, ref: Reference, ctype: CitationType, page: str | None = None) -> str:
        """Build a Citation from a Reference and format it."""
        author_names = [a.last_name for a in ref.authors] if ref.authors else ["?"]
        citation = Citation(
            citation_type=ctype,
            authors=author_names,
            year=ref.year,
            page=page,
        )
        return citation.format_apa()

    def _insert_parenthetical(self) -> None:
        ref = self._get_selected()
        if ref:
            text = self._build_citation(ref, CitationType.PARENTHETICAL)
            self.citation_requested.emit(text)

    def _insert_narrative(self) -> None:
        ref = self._get_selected()
        if ref:
            text = self._build_citation(ref, CitationType.NARRATIVE)
            self.citation_requested.emit(text)

    def _insert_with_page(self) -> None:
        ref = self._get_selected()
        if ref:
            text = self._build_citation(ref, CitationType.PARENTHETICAL, page="XX")
            self.citation_requested.emit(text)


_TOOLBAR_STYLE = """
CitationToolbar {
    background: #FFF8E1;
    border: 1px solid #FFD54F;
    border-radius: 4px;
}
QPushButton {
    background: #FF8F00;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: bold;
}
QPushButton:hover {
    background: #EF6C00;
}
QComboBox {
    padding: 3px 6px;
    border: 1px solid #CCCCCC;
    border-radius: 3px;
    background: white;
}
QLabel {
    font-weight: bold;
    font-size: 9pt;
}
"""
