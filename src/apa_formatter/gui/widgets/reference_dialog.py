"""Dialog for adding/editing a single APA 7 reference.

Shows dynamic fields based on the selected ReferenceType (14 types).
Includes a live APA-formatted preview at the bottom.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.models.document import Author, Reference
from apa_formatter.models.enums import ReferenceType


# Fields relevant for each reference type
_TYPE_FIELDS: dict[ReferenceType, set[str]] = {
    ReferenceType.JOURNAL_ARTICLE: {
        "authors",
        "year",
        "title",
        "source",
        "volume",
        "issue",
        "pages",
        "doi",
        "url",
    },
    ReferenceType.BOOK: {"authors", "year", "title", "source", "edition", "doi", "url"},
    ReferenceType.EDITED_BOOK: {
        "authors",
        "year",
        "title",
        "source",
        "edition",
        "editors",
        "doi",
        "url",
    },
    ReferenceType.BOOK_CHAPTER: {
        "authors",
        "year",
        "title",
        "source",
        "editors",
        "pages",
        "doi",
        "url",
    },
    ReferenceType.WEBPAGE: {"authors", "year", "title", "source", "url", "retrieval_date"},
    ReferenceType.CONFERENCE_PAPER: {"authors", "year", "title", "source", "doi", "url"},
    ReferenceType.DISSERTATION: {"authors", "year", "title", "source", "url"},
    ReferenceType.REPORT: {"authors", "year", "title", "source", "url"},
    ReferenceType.NEWSPAPER: {"authors", "year", "title", "source", "pages", "url"},
    ReferenceType.MAGAZINE: {
        "authors",
        "year",
        "title",
        "source",
        "volume",
        "issue",
        "pages",
        "url",
    },
    ReferenceType.SOFTWARE: {"authors", "year", "title", "source", "url"},
    ReferenceType.AUDIOVISUAL: {"authors", "year", "title", "source", "url"},
    ReferenceType.SOCIAL_MEDIA: {"authors", "year", "title", "source", "url"},
    ReferenceType.LEGAL: {"title", "year", "source", "url"},
}


class ReferenceDialog(QDialog):
    """Modal dialog for creating or editing a Reference."""

    def __init__(
        self,
        parent: QWidget | None = None,
        reference: Reference | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Agregar Referencia" if reference is None else "Editar Referencia")
        self.setMinimumSize(600, 550)
        self._result_ref: Reference | None = None

        layout = QVBoxLayout(self)

        # ── Type selector ─────────────────────────────────────────────────
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Tipo de referencia:"))
        self._type_combo = QComboBox()
        for rt in ReferenceType:
            self._type_combo.addItem(rt.value, rt)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self._type_combo, stretch=1)
        layout.addLayout(type_row)

        # ── Authors group ─────────────────────────────────────────────────
        self._authors_group = QGroupBox("Autores")
        ag_layout = QVBoxLayout(self._authors_group)
        self._authors_list = QListWidget()
        self._authors_list.setMaximumHeight(80)
        ag_layout.addWidget(self._authors_list)

        author_row = QHBoxLayout()
        self._author_last = QLineEdit()
        self._author_last.setPlaceholderText("Apellido")
        self._author_first = QLineEdit()
        self._author_first.setPlaceholderText("Nombre")
        self._author_mi = QLineEdit()
        self._author_mi.setPlaceholderText("Inicial")
        self._author_mi.setMaximumWidth(60)
        btn_add = QPushButton("➕")
        btn_add.clicked.connect(self._add_author)
        btn_remove = QPushButton("🗑")
        btn_remove.clicked.connect(self._remove_author)
        author_row.addWidget(self._author_last, stretch=2)
        author_row.addWidget(self._author_first, stretch=2)
        author_row.addWidget(self._author_mi)
        author_row.addWidget(btn_add)
        author_row.addWidget(btn_remove)
        ag_layout.addLayout(author_row)
        layout.addWidget(self._authors_group)

        # ── Fields form ───────────────────────────────────────────────────
        self._form = QFormLayout()

        self._year = QLineEdit()
        self._year.setPlaceholderText("2024")
        self._year.setMaximumWidth(100)
        self._form.addRow("Año:", self._year)

        self._title = QLineEdit()
        self._title.setPlaceholderText("Título del trabajo")
        self._form.addRow("Título:", self._title)

        self._source = QLineEdit()
        self._source.setPlaceholderText("Nombre de la revista, editorial, sitio web…")
        self._form.addRow("Fuente:", self._source)

        self._volume = QLineEdit()
        self._volume.setPlaceholderText("Ej: 42")
        self._volume.setMaximumWidth(100)
        self._form.addRow("Volumen:", self._volume)

        self._issue = QLineEdit()
        self._issue.setPlaceholderText("Ej: 3")
        self._issue.setMaximumWidth(100)
        self._form.addRow("Número:", self._issue)

        self._pages = QLineEdit()
        self._pages.setPlaceholderText("Ej: 123-145")
        self._pages.setMaximumWidth(150)
        self._form.addRow("Páginas:", self._pages)

        self._edition = QLineEdit()
        self._edition.setPlaceholderText("Ej: 3rd")
        self._edition.setMaximumWidth(100)
        self._form.addRow("Edición:", self._edition)

        self._doi = QLineEdit()
        self._doi.setPlaceholderText("Ej: 10.1037/amp0000001")
        self._form.addRow("DOI:", self._doi)

        self._url = QLineEdit()
        self._url.setPlaceholderText("https://…")
        self._form.addRow("URL:", self._url)

        self._retrieval_date = QDateEdit()
        self._retrieval_date.setCalendarPopup(True)
        self._retrieval_date.setDate(date.today())
        self._form.addRow("Fecha de consulta:", self._retrieval_date)

        # Editors group (for book chapters, edited books)
        self._editors_group = QGroupBox("Editores")
        eg_layout = QVBoxLayout(self._editors_group)
        self._editors_list = QListWidget()
        self._editors_list.setMaximumHeight(60)
        eg_layout.addWidget(self._editors_list)
        editor_row = QHBoxLayout()
        self._editor_last = QLineEdit()
        self._editor_last.setPlaceholderText("Apellido")
        self._editor_first = QLineEdit()
        self._editor_first.setPlaceholderText("Nombre")
        btn_add_ed = QPushButton("➕")
        btn_add_ed.clicked.connect(self._add_editor)
        btn_rm_ed = QPushButton("🗑")
        btn_rm_ed.clicked.connect(self._remove_editor)
        editor_row.addWidget(self._editor_last, stretch=2)
        editor_row.addWidget(self._editor_first, stretch=2)
        editor_row.addWidget(btn_add_ed)
        editor_row.addWidget(btn_rm_ed)
        eg_layout.addLayout(editor_row)
        self._form.addRow(self._editors_group)

        layout.addLayout(self._form)

        # ── Live preview ──────────────────────────────────────────────────
        layout.addWidget(QLabel("Vista previa APA:"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(70)
        self._preview.setStyleSheet(
            "background: #FFFDE7; border: 1px solid #E0D97D; font-size: 10pt; padding: 4px;"
        )
        layout.addWidget(self._preview)

        # ── Buttons ───────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect text changes for live preview
        for field in (
            self._year,
            self._title,
            self._source,
            self._volume,
            self._issue,
            self._pages,
            self._edition,
            self._doi,
            self._url,
        ):
            field.textChanged.connect(self._update_preview)

        # Populate from existing reference
        if reference:
            self._populate(reference)

        self._on_type_changed()  # initial visibility
        self._update_preview()

        self.setStyleSheet(_DIALOG_STYLE)

    # ── Populate from existing ────────────────────────────────────────────

    def _populate(self, ref: Reference) -> None:
        idx = self._type_combo.findData(ref.ref_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        for a in ref.authors:
            self._authors_list.addItem(f"{a.last_name}, {a.first_name}")
        self._year.setText(str(ref.year) if ref.year else "")
        self._title.setText(ref.title)
        self._source.setText(ref.source)
        self._volume.setText(ref.volume or "")
        self._issue.setText(ref.issue or "")
        self._pages.setText(ref.pages or "")
        self._edition.setText(ref.edition or "")
        self._doi.setText(ref.doi or "")
        self._url.setText(ref.url or "")
        if ref.retrieval_date:
            self._retrieval_date.setDate(ref.retrieval_date)
        for e in ref.editors:
            self._editors_list.addItem(f"{e.last_name}, {e.first_name}")

    # ── Type-based field visibility ───────────────────────────────────────

    def _on_type_changed(self) -> None:
        rt = self._type_combo.currentData()
        fields = _TYPE_FIELDS.get(rt, set())

        self._authors_group.setVisible("authors" in fields)
        # Row visibility via label + widget
        _set_form_row_visible(self._form, self._volume, "volume" in fields)
        _set_form_row_visible(self._form, self._issue, "issue" in fields)
        _set_form_row_visible(self._form, self._pages, "pages" in fields)
        _set_form_row_visible(self._form, self._edition, "edition" in fields)
        _set_form_row_visible(self._form, self._retrieval_date, "retrieval_date" in fields)
        self._editors_group.setVisible("editors" in fields)

        self._update_preview()

    # ── Author management ─────────────────────────────────────────────────

    def _add_author(self) -> None:
        last = self._author_last.text().strip()
        first = self._author_first.text().strip()
        if last and first:
            mi = self._author_mi.text().strip()
            display = f"{last}, {first}" + (f" {mi}." if mi else "")
            self._authors_list.addItem(display)
            self._author_last.clear()
            self._author_first.clear()
            self._author_mi.clear()
            self._update_preview()

    def _remove_author(self) -> None:
        row = self._authors_list.currentRow()
        if row >= 0:
            self._authors_list.takeItem(row)
            self._update_preview()

    def _add_editor(self) -> None:
        last = self._editor_last.text().strip()
        first = self._editor_first.text().strip()
        if last and first:
            self._editors_list.addItem(f"{last}, {first}")
            self._editor_last.clear()
            self._editor_first.clear()
            self._update_preview()

    def _remove_editor(self) -> None:
        row = self._editors_list.currentRow()
        if row >= 0:
            self._editors_list.takeItem(row)
            self._update_preview()

    # ── Build Reference ───────────────────────────────────────────────────

    def _build_reference(self) -> Reference:
        authors = []
        for i in range(self._authors_list.count()):
            text = self._authors_list.item(i).text()
            parts = text.split(", ", 1)
            last = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            rest_parts = rest.split(" ", 1)
            first = rest_parts[0]
            mi = rest_parts[1].rstrip(".") if len(rest_parts) > 1 else None
            authors.append(Author(last_name=last, first_name=first, middle_initial=mi))

        editors = []
        for i in range(self._editors_list.count()):
            text = self._editors_list.item(i).text()
            parts = text.split(", ", 1)
            editors.append(
                Author(
                    last_name=parts[0],
                    first_name=parts[1] if len(parts) > 1 else "",
                )
            )

        year_text = self._year.text().strip()

        return Reference(
            ref_type=self._type_combo.currentData(),
            authors=authors,
            year=int(year_text) if year_text.isdigit() else None,
            title=self._title.text().strip(),
            source=self._source.text().strip(),
            volume=self._volume.text().strip() or None,
            issue=self._issue.text().strip() or None,
            pages=self._pages.text().strip() or None,
            doi=self._doi.text().strip() or None,
            url=self._url.text().strip() or None,
            edition=self._edition.text().strip() or None,
            editors=editors,
            retrieval_date=(
                self._retrieval_date.date().toPython() if self._retrieval_date.isVisible() else None
            ),
        )

    # ── Live preview ──────────────────────────────────────────────────────

    def _update_preview(self) -> None:
        try:
            ref = self._build_reference()
            self._preview.setPlainText(ref.format_apa())
        except Exception:
            self._preview.setPlainText("(preview not available)")

    # ── Accept ────────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        self._result_ref = self._build_reference()
        self.accept()

    def get_reference(self) -> Reference | None:
        return self._result_ref


# ── Helpers ───────────────────────────────────────────────────────────────


def _set_form_row_visible(form: QFormLayout, widget: QWidget, visible: bool) -> None:
    """Show/hide a form row by its field widget."""
    for i in range(form.rowCount()):
        item = form.itemAt(i, QFormLayout.ItemRole.FieldRole)
        label_item = form.itemAt(i, QFormLayout.ItemRole.LabelRole)
        if item and item.widget() is widget:
            widget.setVisible(visible)
            if label_item and label_item.widget():
                label_item.widget().setVisible(visible)
            break


# ── Stylesheet ────────────────────────────────────────────────────────────

_DIALOG_STYLE = """
QDialog {
    background: white;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #DDDDDD;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLineEdit, QDateEdit {
    border: 1px solid #CCCCCC;
    border-radius: 3px;
    padding: 4px 6px;
    font-size: 10pt;
}
QLineEdit:focus {
    border-color: #4A90D9;
}
QPushButton {
    background: #4A90D9;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 4px 10px;
    font-size: 9pt;
}
QPushButton:hover {
    background: #357ABD;
}
QComboBox {
    padding: 4px 8px;
    border: 1px solid #BBBBBB;
    border-radius: 3px;
    background: white;
}
"""
