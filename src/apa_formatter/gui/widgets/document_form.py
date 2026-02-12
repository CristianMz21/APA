"""Structured document editor for APA 7 documents.

Replaces the plain text editor with a multi-tab form that maps 1:1
to the APADocument Pydantic model fields.

Tabs
────
  1. Portada      — Title page fields
  2. Resumen      — Abstract + keywords
  3. Secciones    — Hierarchical section tree
  4. Referencias  — Reference list (CRUD + APA sort)
  5. Apéndices    — Appendix sections
  6. Opciones     — TOC toggle, output format
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.models.document import (
    APADocument,
    Reference,
    Section,
    TitlePage,
)
from apa_formatter.models.enums import (
    DocumentVariant,
    FontChoice,
    HeadingLevel,
    OutputFormat,
)


# ═══════════════════════════════════════════════════════════════════════════
# Main Widget
# ═══════════════════════════════════════════════════════════════════════════


class DocumentFormWidget(QWidget):
    """Multi-tab form editor for structured APA document creation."""

    # Emitted whenever any field changes (for live-preview if desired)
    document_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Build tabs
        self._portada = _PortadaTab()
        self._resumen = _ResumenTab()
        self._secciones = _SeccionesTab()
        self._referencias = _ReferenciasTab()
        self._apendices = _ApendicesTab()
        self._opciones = _OpcionesTab()

        self._tabs.addTab(self._portada, "📄 Portada")
        self._tabs.addTab(self._resumen, "📝 Resumen")
        self._tabs.addTab(self._secciones, "📑 Secciones")
        self._tabs.addTab(self._referencias, "📚 Referencias")
        self._tabs.addTab(self._apendices, "📎 Apéndices")
        self._tabs.addTab(self._opciones, "⚙️ Opciones")

        # Sync citation toolbar when switching to Secciones tab
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Wire live-preview: connect sub-widget changes → document_changed
        self._connect_change_signals()

        self.setStyleSheet(_get_form_style())

    def _connect_change_signals(self) -> None:
        """Connect sub-widget signals to emit document_changed for live preview."""

        def emit(*_args: object) -> None:
            self.document_changed.emit()

        # Portada fields (textChanged(str) → 1 arg)
        self._portada._title.textChanged.connect(emit)
        self._portada._affiliation.textChanged.connect(emit)
        self._portada._course.textChanged.connect(emit)
        self._portada._instructor.textChanged.connect(emit)

        # Resumen fields
        self._resumen._abstract.textChanged.connect(emit)  # 0 args (QPlainTextEdit)
        self._resumen._keywords.textChanged.connect(emit)  # 1 arg (QLineEdit)

        # Secciones / Apéndices tree content
        self._secciones._content_edit.textChanged.connect(emit)
        self._secciones._heading_input.textChanged.connect(emit)
        self._apendices._content_edit.textChanged.connect(emit)

    # ── Public API ────────────────────────────────────────────────────────

    def build_document(
        self,
        font: FontChoice = FontChoice.TIMES_NEW_ROMAN,
        variant: DocumentVariant = DocumentVariant.STUDENT,
    ) -> APADocument:
        """Collect all form data and build an APADocument model."""
        title_page = self._portada.get_title_page(variant)
        abstract = self._resumen.get_abstract()
        keywords = self._resumen.get_keywords()
        sections = self._secciones.get_sections()
        appendices = self._apendices.get_sections()
        include_toc = self._opciones.get_include_toc()

        return APADocument(
            title_page=title_page,
            abstract=abstract if abstract else None,
            keywords=keywords,
            sections=sections,
            references=self._referencias.get_references(),
            appendices=appendices,
            font=font,
            output_format=OutputFormat.DOCX,
            include_toc=include_toc,
        )

    def set_document(self, doc: APADocument) -> None:
        """Populate form fields from an existing APADocument."""
        self._portada.set_title_page(doc.title_page)
        self._resumen.set_abstract(doc.abstract or "")
        self._resumen.set_keywords(doc.keywords)
        self._secciones.set_sections(doc.sections)
        self._referencias.set_references(doc.references)
        self._apendices.set_sections(doc.appendices)
        self._opciones.set_include_toc(doc.include_toc)

    def set_references(self, refs: list[Reference]) -> None:
        """Store references via the references tab widget."""
        self._referencias.set_references(refs)

    def get_references(self) -> list[Reference]:
        """Return current references from the references tab."""
        return self._referencias.get_references()

    def clear(self) -> None:
        """Reset all form fields."""
        self._portada.clear()
        self._resumen.clear()
        self._secciones.clear()
        self._referencias.clear()
        self._apendices.clear()
        self._opciones.clear()

    def _on_tab_changed(self, index: int) -> None:
        """Sync citation toolbar when switching to the Secciones tab."""
        if index == 2:  # Secciones tab
            refs = self._referencias.get_references()
            self._secciones.set_citation_references(refs)


# ═══════════════════════════════════════════════════════════════════════════
# Tab 1: Portada (Title Page)
# ═══════════════════════════════════════════════════════════════════════════


class _PortadaTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._title = QLineEdit()
        self._title.setPlaceholderText("Título del trabajo (bold, centrado)")
        form.addRow("Título:", self._title)

        # Authors list
        authors_group = QGroupBox("Autores")
        authors_layout = QVBoxLayout(authors_group)
        self._authors_list = QListWidget()
        self._authors_list.setMaximumHeight(100)
        authors_layout.addWidget(self._authors_list)

        btn_row = QHBoxLayout()
        self._author_input = QLineEdit()
        self._author_input.setPlaceholderText("Nombre del autor")
        btn_add = QPushButton("➕ Agregar")
        btn_add.clicked.connect(self._add_author)
        self._author_input.returnPressed.connect(self._add_author)
        btn_remove = QPushButton("🗑 Quitar")
        btn_remove.clicked.connect(self._remove_author)
        btn_row.addWidget(self._author_input, stretch=1)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        authors_layout.addLayout(btn_row)

        form.addRow(authors_group)

        self._affiliation = QLineEdit()
        self._affiliation.setPlaceholderText("Afiliación institucional")
        self._affiliation.setText("Universidad")
        form.addRow("Afiliación:", self._affiliation)

        self._course = QLineEdit()
        self._course.setPlaceholderText("Ej: PSY 301: Métodos de Investigación (solo estudiante)")
        form.addRow("Curso:", self._course)

        self._instructor = QLineEdit()
        self._instructor.setPlaceholderText("Nombre del instructor (solo estudiante)")
        form.addRow("Instructor:", self._instructor)

        self._due_date = QDateEdit()
        self._due_date.setCalendarPopup(True)
        self._due_date.setDate(date.today())
        form.addRow("Fecha:", self._due_date)

        self._running_head = QLineEdit()
        self._running_head.setPlaceholderText("Título corto ≤50 chars (solo profesional)")
        self._running_head.setMaxLength(50)
        form.addRow("Running Head:", self._running_head)

        self._author_note = QTextEdit()
        self._author_note.setPlaceholderText("Nota del autor (solo profesional)")
        self._author_note.setMaximumHeight(80)
        form.addRow("Nota del Autor:", self._author_note)

        layout.addLayout(form)
        layout.addStretch()

    def _add_author(self) -> None:
        name = self._author_input.text().strip()
        if name:
            self._authors_list.addItem(name)
            self._author_input.clear()

    def _remove_author(self) -> None:
        row = self._authors_list.currentRow()
        if row >= 0:
            self._authors_list.takeItem(row)

    def get_title_page(self, variant: DocumentVariant) -> TitlePage:
        authors = []
        for i in range(self._authors_list.count()):
            authors.append(self._authors_list.item(i).text())
        if not authors:
            authors = ["Autor Desconocido"]

        return TitlePage(
            title=self._title.text().strip() or "Sin Título",
            authors=authors,
            affiliation=self._affiliation.text().strip() or "Universidad",
            course=self._course.text().strip() or None,
            instructor=self._instructor.text().strip() or None,
            due_date=self._due_date.date().toPython(),
            running_head=self._running_head.text().strip() or None,
            author_note=self._author_note.toPlainText().strip() or None,
            variant=variant,
        )

    def set_title_page(self, tp: TitlePage) -> None:
        self._title.setText(tp.title)
        self._authors_list.clear()
        for a in tp.authors:
            self._authors_list.addItem(a)
        self._affiliation.setText(tp.affiliation)
        self._course.setText(tp.course or "")
        self._instructor.setText(tp.instructor or "")
        if tp.due_date:
            self._due_date.setDate(tp.due_date)
        self._running_head.setText(tp.running_head or "")
        self._author_note.setPlainText(tp.author_note or "")

    def clear(self) -> None:
        self._title.clear()
        self._authors_list.clear()
        self._affiliation.setText("Universidad")
        self._course.clear()
        self._instructor.clear()
        self._due_date.setDate(date.today())
        self._running_head.clear()
        self._author_note.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Tab 2: Resumen (Abstract + Keywords)
# ═══════════════════════════════════════════════════════════════════════════


class _ResumenTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        # Abstract
        layout.addWidget(QLabel("Resumen (Abstract):"))
        self._abstract = QPlainTextEdit()
        self._abstract.setPlaceholderText("Escriba el resumen del trabajo (150–250 palabras)…")
        self._abstract.textChanged.connect(self._update_word_count)
        layout.addWidget(self._abstract)

        self._word_count_label = QLabel("0 / 250 palabras")
        self._word_count_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self._word_count_label)

        # Keywords
        layout.addWidget(QLabel("Palabras Clave:"))
        self._keywords = QLineEdit()
        self._keywords.setPlaceholderText(
            "inteligencia artificial, educación superior, revisión sistemática"
        )
        tip = QLabel("Separadas por comas — mínimo 3, máximo 5 recomendadas")
        tip.setStyleSheet("color: #888; font-size: 8pt; font-style: italic;")
        layout.addWidget(self._keywords)
        layout.addWidget(tip)
        layout.addStretch()

    def _update_word_count(self) -> None:
        text = self._abstract.toPlainText().strip()
        count = len(text.split()) if text else 0
        color = "#c0392b" if count > 250 else "#27ae60" if count >= 150 else "#e67e22"
        self._word_count_label.setText(f"{count} / 250 palabras")
        self._word_count_label.setStyleSheet(f"color: {color}; font-size: 9pt;")

    def get_abstract(self) -> str:
        return self._abstract.toPlainText().strip()

    def set_abstract(self, text: str) -> None:
        self._abstract.setPlainText(text)

    def get_keywords(self) -> list[str]:
        raw = self._keywords.text().strip()
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]

    def set_keywords(self, keywords: list[str]) -> None:
        self._keywords.setText(", ".join(keywords))

    def clear(self) -> None:
        self._abstract.clear()
        self._keywords.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Tab 3+4: Secciones / Apéndices (shared tree-based editor)
# ═══════════════════════════════════════════════════════════════════════════


_HEADING_LEVELS = {
    "Nivel 1 — Centrado, Negrita": HeadingLevel.LEVEL_1,
    "Nivel 2 — Izquierda, Negrita": HeadingLevel.LEVEL_2,
    "Nivel 3 — Izquierda, Negrita Cursiva": HeadingLevel.LEVEL_3,
    "Nivel 4 — Indentado, Negrita": HeadingLevel.LEVEL_4,
    "Nivel 5 — Indentado, Negrita Cursiva": HeadingLevel.LEVEL_5,
}

_LEVEL_FROM_DESC = {v: k for k, v in _HEADING_LEVELS.items()}


class _SectionTreeWidget(QWidget):
    """A tree + detail panel for editing hierarchical Section objects."""

    def __init__(self, section_label: str = "Sección") -> None:
        super().__init__()
        self._section_label = section_label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # ── Left: Tree ────────────────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_layout.addWidget(QLabel(f"Estructura de {section_label}s:"))
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Encabezado", "Nivel"])
        self._tree.setColumnWidth(0, 200)
        self._tree.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self._tree)

        btn_row = QHBoxLayout()
        btn_add = QPushButton(f"➕ {section_label}")
        btn_add.clicked.connect(self._add_section)
        btn_add_sub = QPushButton("➕ Sub-sección")
        btn_add_sub.clicked.connect(self._add_subsection)
        btn_remove = QPushButton("🗑 Quitar")
        btn_remove.clicked.connect(self._remove_section)
        btn_up = QPushButton("⬆")
        btn_up.setToolTip("Mover arriba")
        btn_up.clicked.connect(self._move_up)
        btn_down = QPushButton("⬇")
        btn_down.setToolTip("Mover abajo")
        btn_down.clicked.connect(self._move_down)

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_add_sub)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_up)
        btn_row.addWidget(btn_down)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        # ── Right: Detail panel ───────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)

        right_layout.addWidget(QLabel("Editar sección seleccionada:"))

        form = QFormLayout()
        self._heading_input = QLineEdit()
        self._heading_input.setPlaceholderText("Título de la sección")
        self._heading_input.textChanged.connect(self._on_heading_edited)
        form.addRow("Encabezado:", self._heading_input)

        self._level_combo = QComboBox()
        self._level_combo.addItems(list(_HEADING_LEVELS.keys()))
        self._level_combo.currentTextChanged.connect(self._on_level_changed)
        form.addRow("Nivel:", self._level_combo)

        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Contenido:"))
        self._content_edit = QPlainTextEdit()
        self._content_edit.setPlaceholderText("Escriba el contenido del párrafo…")
        self._content_edit.textChanged.connect(self._on_content_edited)
        right_layout.addWidget(self._content_edit)

        splitter.addWidget(right)
        splitter.setSizes([250, 400])

        self._updating = False  # guard against recursion

    # ── Tree manipulation ─────────────────────────────────────────────────

    def _add_section(self) -> None:
        item = QTreeWidgetItem(["Nueva Sección", "Nivel 1"])
        item.setData(0, Qt.ItemDataRole.UserRole, HeadingLevel.LEVEL_1)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, "")  # content
        self._tree.addTopLevelItem(item)
        self._tree.setCurrentItem(item)

    def _add_subsection(self) -> None:
        parent = self._tree.currentItem()
        if parent is None:
            self._add_section()
            return
        parent_level = parent.data(0, Qt.ItemDataRole.UserRole) or HeadingLevel.LEVEL_1
        child_level = min(parent_level + 1, 5)
        child_level_enum = HeadingLevel(child_level)

        item = QTreeWidgetItem(["Nueva Sub-sección", f"Nivel {child_level}"])
        item.setData(0, Qt.ItemDataRole.UserRole, child_level_enum)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, "")
        parent.addChild(item)
        parent.setExpanded(True)
        self._tree.setCurrentItem(item)

    def _remove_section(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            idx = self._tree.indexOfTopLevelItem(item)
            self._tree.takeTopLevelItem(idx)

    def _move_up(self) -> None:
        self._move(-1)

    def _move_down(self) -> None:
        self._move(1)

    def _move(self, direction: int) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent:
            idx = parent.indexOfChild(item)
            new_idx = idx + direction
            if 0 <= new_idx < parent.childCount():
                parent.removeChild(item)
                parent.insertChild(new_idx, item)
                self._tree.setCurrentItem(item)
        else:
            idx = self._tree.indexOfTopLevelItem(item)
            new_idx = idx + direction
            if 0 <= new_idx < self._tree.topLevelItemCount():
                self._tree.takeTopLevelItem(idx)
                self._tree.insertTopLevelItem(new_idx, item)
                self._tree.setCurrentItem(item)

    # ── Detail panel sync ─────────────────────────────────────────────────

    def _on_item_selected(self, current: QTreeWidgetItem | None, _prev) -> None:
        if current is None:
            return
        self._updating = True
        self._heading_input.setText(current.text(0))
        level = current.data(0, Qt.ItemDataRole.UserRole) or HeadingLevel.LEVEL_1
        desc = _LEVEL_FROM_DESC.get(level)
        if desc:
            self._level_combo.setCurrentText(desc)
        content = current.data(0, Qt.ItemDataRole.UserRole + 1) or ""
        self._content_edit.setPlainText(content)
        self._updating = False

    def _on_heading_edited(self, text: str) -> None:
        if self._updating:
            return
        item = self._tree.currentItem()
        if item:
            item.setText(0, text)

    def _on_level_changed(self, text: str) -> None:
        if self._updating:
            return
        item = self._tree.currentItem()
        if item and text in _HEADING_LEVELS:
            level = _HEADING_LEVELS[text]
            item.setData(0, Qt.ItemDataRole.UserRole, level)
            item.setText(1, f"Nivel {level.value}")

    def _on_content_edited(self) -> None:
        if self._updating:
            return
        item = self._tree.currentItem()
        if item:
            item.setData(0, Qt.ItemDataRole.UserRole + 1, self._content_edit.toPlainText())

    # ── Serialization ─────────────────────────────────────────────────────

    def get_sections(self) -> list[Section]:
        sections = []
        for i in range(self._tree.topLevelItemCount()):
            sections.append(self._item_to_section(self._tree.topLevelItem(i)))
        return sections

    def _item_to_section(self, item: QTreeWidgetItem) -> Section:
        level = item.data(0, Qt.ItemDataRole.UserRole) or HeadingLevel.LEVEL_1
        content = item.data(0, Qt.ItemDataRole.UserRole + 1) or ""
        subsections = []
        for i in range(item.childCount()):
            subsections.append(self._item_to_section(item.child(i)))
        return Section(
            heading=item.text(0),
            level=level,
            content=content,
            subsections=subsections,
        )

    def set_sections(self, sections: list[Section]) -> None:
        self._tree.clear()
        for sec in sections:
            self._add_section_item(sec, parent=None)

    def _add_section_item(self, sec: Section, parent: QTreeWidgetItem | None) -> QTreeWidgetItem:
        item = QTreeWidgetItem([sec.heading or "Sin título", f"Nivel {sec.level.value}"])
        item.setData(0, Qt.ItemDataRole.UserRole, sec.level)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, sec.content)
        if parent:
            parent.addChild(item)
        else:
            self._tree.addTopLevelItem(item)
        for sub in sec.subsections:
            self._add_section_item(sub, item)
        item.setExpanded(True)
        return item

    def clear(self) -> None:
        self._tree.clear()
        self._heading_input.clear()
        self._content_edit.clear()


class _SeccionesTab(_SectionTreeWidget):
    def __init__(self) -> None:
        super().__init__(section_label="Sección")

        # Add citation toolbar above content editor
        from apa_formatter.gui.widgets.citation_toolbar import CitationToolbar

        self._citation_toolbar = CitationToolbar()
        self._citation_toolbar.citation_requested.connect(self._insert_citation)

        # Find the right panel's layout and insert toolbar before content editor
        right_widget = self.findChildren(QPlainTextEdit)[0].parent()
        right_layout = right_widget.layout()
        # Insert before the content QPlainTextEdit (index of "Contenido:" label)
        content_label_idx = None
        for i in range(right_layout.count()):
            item = right_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QLabel):
                if item.widget().text() == "Contenido:":
                    content_label_idx = i
                    break
        if content_label_idx is not None:
            right_layout.insertWidget(content_label_idx + 1, self._citation_toolbar)

    def set_citation_references(self, refs: list[Reference]) -> None:
        """Update the citation toolbar with available references."""
        self._citation_toolbar.set_references(refs)

    def _insert_citation(self, citation_text: str) -> None:
        """Insert the citation text at the cursor position in the content editor."""
        cursor = self._content_edit.textCursor()
        cursor.insertText(citation_text)
        self._content_edit.setFocus()


class _ApendicesTab(_SectionTreeWidget):
    def __init__(self) -> None:
        super().__init__(section_label="Apéndice")


# ═══════════════════════════════════════════════════════════════════════════
# Tab 4: Referencias
# ═══════════════════════════════════════════════════════════════════════════


class _ReferenciasTab(QWidget):
    """Wrapper around ReferenceListWidget for the tab interface."""

    def __init__(self) -> None:
        super().__init__()
        from apa_formatter.gui.widgets.reference_list import ReferenceListWidget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._ref_list = ReferenceListWidget()
        layout.addWidget(self._ref_list)

    def get_references(self) -> list[Reference]:
        return self._ref_list.get_references()

    def set_references(self, refs: list[Reference]) -> None:
        self._ref_list.set_references(refs)

    def clear(self) -> None:
        self._ref_list.set_references([])


# ═══════════════════════════════════════════════════════════════════════════
# Tab 6: Opciones
# ═══════════════════════════════════════════════════════════════════════════


class _OpcionesTab(QWidget):
    """Full settings panel with page, text, and document options."""

    options_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        # ── Página ────────────────────────────────────────────────────────
        page_group = QGroupBox("Página")
        pg = QFormLayout(page_group)
        pg.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox

        self._margin_top = QDoubleSpinBox()
        self._margin_bottom = QDoubleSpinBox()
        self._margin_left = QDoubleSpinBox()
        self._margin_right = QDoubleSpinBox()
        for sb in (self._margin_top, self._margin_bottom, self._margin_left, self._margin_right):
            sb.setRange(0.5, 10.0)
            sb.setSingleStep(0.1)
            sb.setDecimals(2)
            sb.setSuffix(" cm")
            sb.setValue(2.54)
            sb.valueChanged.connect(lambda _: self.options_changed.emit())

        pg.addRow("Margen superior:", self._margin_top)
        pg.addRow("Margen inferior:", self._margin_bottom)
        pg.addRow("Margen izquierda:", self._margin_left)
        pg.addRow("Margen derecha:", self._margin_right)

        # Binding margin
        self._binding = QCheckBox("Empaste (margen izquierdo extendido)")
        self._binding.toggled.connect(self._on_binding_toggled)
        self._binding.toggled.connect(lambda: self.options_changed.emit())
        pg.addRow(self._binding)

        self._binding_left = QDoubleSpinBox()
        self._binding_left.setRange(2.0, 8.0)
        self._binding_left.setSingleStep(0.5)
        self._binding_left.setDecimals(2)
        self._binding_left.setSuffix(" cm")
        self._binding_left.setValue(4.0)
        self._binding_left.setEnabled(False)
        self._binding_left.valueChanged.connect(lambda _: self.options_changed.emit())
        pg.addRow("  Margen empaste izq:", self._binding_left)

        # Page size selector
        self._page_size = QComboBox()
        self._page_size.addItems(
            [
                "Carta (21.59 × 27.94 cm)",
                "Letter (21.59 × 27.94 cm)",
                "A4 (21.0 × 29.7 cm)",
                "Legal (21.59 × 35.56 cm)",
            ]
        )
        self._page_size.currentTextChanged.connect(lambda: self.options_changed.emit())
        pg.addRow("Tamaño de página:", self._page_size)

        layout.addWidget(page_group)

        # ── Texto ─────────────────────────────────────────────────────────
        text_group = QGroupBox("Formato de Texto")
        tg = QFormLayout(text_group)
        tg.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._alignment = QComboBox()
        self._alignment.addItems(["Izquierda", "Justificado"])
        self._alignment.currentTextChanged.connect(lambda: self.options_changed.emit())
        tg.addRow("Alineación:", self._alignment)

        # Font selector (APA 7 accepted fonts)
        self._font_select = QComboBox()
        self._font_select.addItems(
            [
                "Times New Roman (12pt)",
                "Calibri (11pt)",
                "Arial (11pt)",
                "Georgia (11pt)",
                "Lucida Sans Unicode (10pt)",
                "Computer Modern (10pt)",
            ]
        )
        self._font_select.currentTextChanged.connect(lambda: self.options_changed.emit())
        tg.addRow("Fuente:", self._font_select)

        self._line_spacing = QDoubleSpinBox()
        self._line_spacing.setRange(1.0, 3.0)
        self._line_spacing.setSingleStep(0.5)
        self._line_spacing.setDecimals(1)
        self._line_spacing.setValue(2.0)
        self._line_spacing.valueChanged.connect(lambda _: self.options_changed.emit())
        tg.addRow("Interlineado:", self._line_spacing)

        self._indent = QDoubleSpinBox()
        self._indent.setRange(0.0, 5.0)
        self._indent.setSingleStep(0.1)
        self._indent.setDecimals(2)
        self._indent.setSuffix(" cm")
        self._indent.setValue(1.27)
        self._indent.valueChanged.connect(lambda _: self.options_changed.emit())
        tg.addRow("Sangría primera línea:", self._indent)

        self._space_before = QSpinBox()
        self._space_before.setRange(0, 24)
        self._space_before.setSuffix(" pt")
        self._space_before.setValue(0)
        self._space_before.valueChanged.connect(lambda _: self.options_changed.emit())
        tg.addRow("Espacio antes párrafo:", self._space_before)

        self._space_after = QSpinBox()
        self._space_after.setRange(0, 24)
        self._space_after.setSuffix(" pt")
        self._space_after.setValue(0)
        self._space_after.valueChanged.connect(lambda _: self.options_changed.emit())
        tg.addRow("Espacio después párrafo:", self._space_after)

        layout.addWidget(text_group)

        # ── Documento ─────────────────────────────────────────────────────
        doc_group = QGroupBox("Documento")
        dg = QVBoxLayout(doc_group)

        self._toc = QCheckBox("Incluir Tabla de Contenidos (TOC)")
        self._toc.toggled.connect(lambda: self.options_changed.emit())
        dg.addWidget(self._toc)

        # Running head
        self._running_head = QCheckBox("Incluir encabezado de página (running head)")
        self._running_head.toggled.connect(lambda: self.options_changed.emit())
        dg.addWidget(self._running_head)

        # Page numbering
        num_row = QHBoxLayout()
        num_label = QLabel("Numeración:")
        num_label.setStyleSheet("font-weight: bold;")
        num_row.addWidget(num_label)
        self._page_num_pos = QComboBox()
        self._page_num_pos.addItems(
            ["Esquina superior derecha", "Centro inferior", "Sin numeración"]
        )
        self._page_num_pos.currentTextChanged.connect(lambda: self.options_changed.emit())
        num_row.addWidget(self._page_num_pos)
        dg.addLayout(num_row)

        tip = QLabel("Configuración del documento para exportación APA 7.")
        tip.setStyleSheet("color: #888; font-style: italic; font-size: 9pt;")
        dg.addWidget(tip)

        layout.addWidget(doc_group)
        layout.addStretch()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_binding_toggled(self, checked: bool) -> None:
        self._binding_left.setEnabled(checked)
        if checked:
            self._margin_left.setValue(self._binding_left.value())

    # ── Public API ────────────────────────────────────────────────────────

    def get_include_toc(self) -> bool:
        return self._toc.isChecked()

    def set_include_toc(self, value: bool) -> None:
        self._toc.setChecked(value)

    def get_options(self) -> dict:
        """Return all option values as a flat dict."""
        return {
            "margin_top_cm": self._margin_top.value(),
            "margin_bottom_cm": self._margin_bottom.value(),
            "margin_left_cm": self._margin_left.value(),
            "margin_right_cm": self._margin_right.value(),
            "binding_enabled": self._binding.isChecked(),
            "binding_left_cm": self._binding_left.value(),
            "page_size": self._page_size.currentText().split(" (")[0],
            "alignment": self._alignment.currentText().lower(),
            "font_name": self._font_select.currentText().split(" (")[0],
            "line_spacing": self._line_spacing.value(),
            "indent_cm": self._indent.value(),
            "space_before_pt": self._space_before.value(),
            "space_after_pt": self._space_after.value(),
            "include_toc": self._toc.isChecked(),
            "running_head": self._running_head.isChecked(),
            "page_num_position": self._page_num_pos.currentText(),
        }

    def set_options(self, opts: dict) -> None:
        """Populate controls from a dict (e.g. from config)."""
        if "margin_top_cm" in opts:
            self._margin_top.setValue(opts["margin_top_cm"])
        if "margin_bottom_cm" in opts:
            self._margin_bottom.setValue(opts["margin_bottom_cm"])
        if "margin_left_cm" in opts:
            self._margin_left.setValue(opts["margin_left_cm"])
        if "margin_right_cm" in opts:
            self._margin_right.setValue(opts["margin_right_cm"])
        if "binding_enabled" in opts:
            self._binding.setChecked(opts["binding_enabled"])
        if "binding_left_cm" in opts:
            self._binding_left.setValue(opts["binding_left_cm"])
        if "page_size" in opts:
            # Find matching page size
            for i in range(self._page_size.count()):
                if self._page_size.itemText(i).startswith(opts["page_size"]):
                    self._page_size.setCurrentIndex(i)
                    break
        if "alignment" in opts:
            idx = 1 if opts["alignment"] == "justificado" else 0
            self._alignment.setCurrentIndex(idx)
        if "font_name" in opts:
            for i in range(self._font_select.count()):
                if self._font_select.itemText(i).startswith(opts["font_name"]):
                    self._font_select.setCurrentIndex(i)
                    break
        if "line_spacing" in opts:
            self._line_spacing.setValue(opts["line_spacing"])
        if "indent_cm" in opts:
            self._indent.setValue(opts["indent_cm"])
        if "space_before_pt" in opts:
            self._space_before.setValue(opts["space_before_pt"])
        if "space_after_pt" in opts:
            self._space_after.setValue(opts["space_after_pt"])
        if "include_toc" in opts:
            self._toc.setChecked(opts["include_toc"])
        if "running_head" in opts:
            self._running_head.setChecked(opts["running_head"])
        if "page_num_position" in opts:
            for i in range(self._page_num_pos.count()):
                if self._page_num_pos.itemText(i) == opts["page_num_position"]:
                    self._page_num_pos.setCurrentIndex(i)
                    break

    def set_from_config(self, config) -> None:
        """Populate controls from an APAConfig instance."""
        m = config.configuracion_pagina.margenes
        self._margin_top.setValue(m.superior_cm)
        self._margin_bottom.setValue(m.inferior_cm)
        self._margin_left.setValue(m.izquierda_cm)
        self._margin_right.setValue(m.derecha_cm)
        if m.condicion_empaste:
            self._binding.setChecked(True)
            self._binding_left.setValue(m.condicion_empaste.izquierda_cm)
        else:
            self._binding.setChecked(False)

        # Page size from config
        ps = config.configuracion_pagina.tamaño_papel
        for i in range(self._page_size.count()):
            if self._page_size.itemText(i).startswith(ps.nombre):
                self._page_size.setCurrentIndex(i)
                break

        tf = config.formato_texto
        self._alignment.setCurrentIndex(1 if tf.justificado else 0)
        self._line_spacing.setValue(tf.interlineado_general)
        self._indent.setValue(tf.sangria_parrafo.medida_cm)
        self._space_before.setValue(tf.espaciado_parrafos.anterior_pt)
        self._space_after.setValue(tf.espaciado_parrafos.posterior_pt)

    def clear(self) -> None:
        self._margin_top.setValue(2.54)
        self._margin_bottom.setValue(2.54)
        self._margin_left.setValue(2.54)
        self._margin_right.setValue(2.54)
        self._binding.setChecked(False)
        self._binding_left.setValue(4.0)
        self._page_size.setCurrentIndex(0)
        self._alignment.setCurrentIndex(0)
        self._font_select.setCurrentIndex(0)
        self._line_spacing.setValue(2.0)
        self._indent.setValue(1.27)
        self._space_before.setValue(0)
        self._space_after.setValue(0)
        self._toc.setChecked(False)
        self._running_head.setChecked(False)
        self._page_num_pos.setCurrentIndex(0)


# ═══════════════════════════════════════════════════════════════════════════
# Stylesheet — generated from theme
# ═══════════════════════════════════════════════════════════════════════════


def _get_form_style() -> str:
    """Build form stylesheet from centralized theme."""
    try:
        from apa_formatter.gui.theme import Theme

        return (
            Theme.tab_widget()
            + Theme.form_inputs()
            + Theme.group_box()
            + Theme.button_primary()
            + Theme.table()
        )
    except ImportError:
        return ""
