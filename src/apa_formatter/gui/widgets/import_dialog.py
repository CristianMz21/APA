"""Dynamic DOCX import dialog powered by SemanticImporter.

Two-phase flow:
  1. Select file → SemanticImporter runs in background → rich results displayed
  2. User reviews/edits metadata, selects references → imports as APADocument

Replaces the legacy DocumentAnalyzer integration with the full semantic
analysis pipeline (parser → handler chain → builder).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.models.document import (
    APADocument,
    Section,
    TitlePage,
)
from apa_formatter.models.semantic_document import (
    DetectedConfig,
    SemanticDocument,
    TitlePageData,
)


# ---------------------------------------------------------------------------
# Background worker — runs SemanticImporter in a QThread
# ---------------------------------------------------------------------------


class _SemanticWorker(QThread):
    """Run SemanticImporter.import_document() in a background thread."""

    finished = Signal(object)  # SemanticDocument
    error = Signal(str)

    def __init__(
        self,
        path: Path,
        *,
        use_ai: bool = False,
        gemini_client: object | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._use_ai = use_ai
        self._gemini_client = gemini_client

    def run(self) -> None:
        try:
            from apa_formatter.importers.semantic_importer import SemanticImporter

            importer = SemanticImporter(gemini_client=self._gemini_client)
            result = importer.import_document(self._path, use_ai=self._use_ai)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------


class ImportDialog(QDialog):
    """Semantic import dialog with deep analysis intelligence."""

    def __init__(self, parent: QWidget | None = None, filepath: Path | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("📥 Importación Semántica de documento")
        self.setMinimumSize(860, 660)

        self._result_doc: APADocument | None = None
        self._semantic_doc: SemanticDocument | None = None
        self._worker: _SemanticWorker | None = None
        self._initial_filepath = filepath

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Detect AI availability
        self._ai_available = False
        self._gemini_client: object | None = None
        try:
            from apa_formatter.bootstrap import Container

            container = Container()
            self._ai_available = container.has_ai
            self._gemini_client = container.gemini_client
        except Exception:
            pass  # AI unavailable — container init failed

        # ── Header ──────────────────────────────────────────────────────────
        header = QLabel(
            "<b>Importación semántica</b> — Análisis profundo con detección"
            " de estructura, idioma, formato y referencias."
        )
        header.setWordWrap(True)
        header.setStyleSheet("font-size: 10pt; padding: 4px;")
        layout.addWidget(header)

        # ── File selector ───────────────────────────────────────────────────
        file_row = QHBoxLayout()
        self._path_label = QLabel("Ningún archivo seleccionado")
        self._path_label.setStyleSheet("color: #888; font-style: italic; padding: 4px;")
        btn_browse = QPushButton("📂 Seleccionar documento")
        btn_browse.clicked.connect(self._on_browse)
        btn_browse.setStyleSheet(_BTN_STYLE)
        file_row.addWidget(self._path_label, stretch=1)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # ── AI toggle ───────────────────────────────────────────────────────
        ai_row = QHBoxLayout()
        self._ai_checkbox = QCheckBox("🤖 Enriquecer con Gemini AI")
        self._ai_checkbox.setEnabled(self._ai_available)
        self._ai_checkbox.setChecked(self._ai_available)
        self._ai_checkbox.setToolTip(
            "Usa Gemini AI para mejorar la extracción de portada, resumen, "
            "palabras clave y referencias.\n\n"
            + (
                "✅ API key configurada — AI disponible"
                if self._ai_available
                else "⚠️ Configura GEMINI_API_KEY en .env para activar"
            )
        )
        self._ai_checkbox.setStyleSheet(
            "QCheckBox { font-size: 10pt; padding: 4px; }"
            + (
                " QCheckBox { color: #8E44AD; font-weight: bold; }"
                if self._ai_available
                else " QCheckBox { color: #999; }"
            )
        )
        ai_row.addWidget(self._ai_checkbox)

        if not self._ai_available:
            ai_hint = QLabel(
                "<small style='color: #999;'>⚠️ Configura GEMINI_API_KEY en .env</small>"
            )
            ai_row.addWidget(ai_hint)

        ai_row.addStretch()
        layout.addLayout(ai_row)

        # ── Progress bar ────────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(6)
        self._progress.setStyleSheet(
            "QProgressBar { border: none; background: #EEEEEE; border-radius: 3px; }"
            "QProgressBar::chunk { background: #4A90D9; border-radius: 3px; }"
        )
        layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #4A90D9; font-size: 9pt; font-style: italic;")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        # ── Analysis content (scrollable) ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._content_widget)
        layout.addWidget(scroll, stretch=1)

        # Placeholder (populated after analysis)
        self._build_placeholder()

        # ── Buttons ─────────────────────────────────────────────────────────
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("📥 Importar")
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setStyleSheet(_DIALOG_STYLE)

        # Auto-start analysis if filepath was provided (e.g. drag & drop)
        if self._initial_filepath and self._initial_filepath.exists():
            self._path_label.setText(str(self._initial_filepath))
            self._path_label.setStyleSheet("color: #333; font-weight: bold; padding: 4px;")
            from PySide6.QtCore import QTimer

            QTimer.singleShot(100, lambda: self._start_analysis(self._initial_filepath))

    # ── Placeholder ─────────────────────────────────────────────────────────

    def _build_placeholder(self) -> None:
        """Show placeholder message before file is selected."""
        self._placeholder = QLabel(
            "Selecciona un archivo .docx para comenzar el análisis semántico.\n\n"
            "El pipeline de análisis extraerá automáticamente:\n"
            "  • Portada (título, autores, afiliación, fecha)\n"
            "  • Resumen y palabras clave\n"
            "  • Estructura jerárquica del cuerpo (con niveles APA)\n"
            "  • Referencias (texto crudo + parseado APA)\n"
            "  • Configuración detectada (idioma, fuentes, interlineado)"
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #999; font-size: 10pt; padding: 40px; line-height: 1.6;"
        )
        self._content_layout.addWidget(self._placeholder)

    # ── File selection ──────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir documento", "", "Documentos (*.docx *.pdf)"
        )
        if not path:
            return
        self._path_label.setText(path)
        self._path_label.setStyleSheet("color: #333; font-weight: bold;")
        self._start_analysis(Path(path))

    def _start_analysis(self, path: Path) -> None:
        """Kick off background semantic analysis."""
        use_ai = self._ai_checkbox.isChecked() and self._ai_available

        self._progress.setVisible(True)
        if use_ai:
            self._status_label.setText("🤖 Analizando con Gemini AI + pipeline semántico…")
        else:
            self._status_label.setText("🔍 Analizando documento con pipeline semántico…")
        self._status_label.setVisible(True)
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self._worker = _SemanticWorker(
            path,
            use_ai=use_ai,
            gemini_client=self._gemini_client if use_ai else None,
            parent=self,
        )
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    def _on_analysis_done(self, result: SemanticDocument) -> None:
        self._progress.setVisible(False)
        self._status_label.setVisible(False)
        self._semantic_doc = result

        self._build_analysis_panels(result)
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _on_analysis_error(self, msg: str) -> None:
        self._progress.setVisible(False)
        self._status_label.setVisible(False)
        self._show_error(msg)

    def _show_error(self, msg: str) -> None:
        self._clear_content()
        lbl = QLabel(f"❌ {msg}")
        lbl.setStyleSheet("color: red; font-size: 10pt; padding: 20px;")
        lbl.setWordWrap(True)
        self._content_layout.addWidget(lbl)

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Analysis panels ─────────────────────────────────────────────────────

    def _build_analysis_panels(self, result: SemanticDocument) -> None:
        self._clear_content()
        lay = self._content_layout

        # 1. Detected config summary bar
        lay.addWidget(self._build_config_bar(result.detected_config))

        # 2. Editable title page metadata
        lay.addWidget(self._build_title_page_panel(result))

        # Splitter: structure | references
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 3. Body structure tree
        splitter.addWidget(self._build_structure_panel(result))

        # 4. References panel
        splitter.addWidget(self._build_references_panel(result))

        splitter.setSizes([380, 450])
        lay.addWidget(splitter, stretch=1)

        # 5. Auto-apply config checkbox
        lay.addWidget(self._build_config_checkbox())

    # -- Panel 1: Detected config bar --

    def _build_config_bar(self, config: DetectedConfig) -> QWidget:
        box = QGroupBox("🔍 Configuración Detectada")
        box.setStyleSheet(_GROUP_STYLE)
        hlay = QHBoxLayout(box)
        hlay.setContentsMargins(8, 4, 8, 4)

        # AI badge (if AI enrichment was used)
        if self._ai_checkbox.isChecked() and self._ai_available:
            ai_badge = QLabel("<b style='color: #8E44AD;'>🤖 AI</b>")
            ai_badge.setToolTip("Este análisis fue enriquecido con Gemini AI")
            hlay.addWidget(ai_badge)

        # Language badge
        lang_text = "🇪🇸 Español" if config.language.value == "es" else "🇺🇸 English"
        lang_color = "#27AE60" if config.language.value == "es" else "#3498DB"
        lang_lbl = QLabel(f"<b style='color: {lang_color}'>{lang_text}</b>")
        hlay.addWidget(lang_lbl)

        self._add_config_item(hlay, "Portada", "✅" if config.has_title_page else "❌")
        self._add_config_item(hlay, "Abstract", "✅" if config.has_abstract else "❌")

        # Fonts
        if config.detected_fonts:
            fonts = ", ".join(config.detected_fonts[:3])
            self._add_config_item(hlay, "Fuentes", fonts)

        # Line spacing
        if config.line_spacing is not None:
            self._add_config_item(hlay, "Interlineado", f"{config.line_spacing:.1f}")

        # Page size
        if config.page_size:
            self._add_config_item(
                hlay,
                "Página",
                f"{config.page_size.nombre} ({config.page_size.ancho_cm:.1f}×{config.page_size.alto_cm:.1f}cm)",
            )

        hlay.addStretch()
        return box

    @staticmethod
    def _add_config_item(layout: QHBoxLayout, label: str, value: str) -> None:
        vl = QVBoxLayout()
        vl.setSpacing(0)
        lbl = QLabel(f"<small>{label}</small>")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val = QLabel(f"<b>{value}</b>")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val.setStyleSheet("font-size: 9pt;")
        vl.addWidget(lbl)
        vl.addWidget(val)
        layout.addLayout(vl)

    # -- Panel 2: TitlePage metadata (editable) --

    def _build_title_page_panel(self, result: SemanticDocument) -> QWidget:
        tp = result.title_page or TitlePageData()
        confidence = tp.confidence

        # Confidence badge
        if confidence >= 0.7:
            conf_text = f"🟢 {confidence:.0%}"
        elif confidence >= 0.4:
            conf_text = f"🟡 {confidence:.0%}"
        else:
            conf_text = f"🔴 {confidence:.0%}"

        box = QGroupBox(f"✏️ Portada Detectada — Confianza: {conf_text}")
        box.setStyleSheet(_GROUP_STYLE)
        form = QFormLayout(box)
        form.setContentsMargins(8, 4, 8, 4)

        self._edit_title = QLineEdit(tp.title)
        self._edit_title.setPlaceholderText("Título del documento")
        form.addRow("Título:", self._edit_title)

        self._edit_authors = QLineEdit(", ".join(tp.authors))
        self._edit_authors.setPlaceholderText("Autor1, Autor2, ...")
        form.addRow("Autores:", self._edit_authors)

        self._edit_affiliation = QLineEdit(tp.affiliation or "")
        self._edit_affiliation.setPlaceholderText("Institución / Universidad")
        form.addRow("Afiliación:", self._edit_affiliation)

        self._edit_course = QLineEdit(tp.course or "")
        self._edit_course.setPlaceholderText("Nombre del curso (si aplica)")
        form.addRow("Curso:", self._edit_course)

        self._edit_instructor = QLineEdit(tp.instructor or "")
        self._edit_instructor.setPlaceholderText("Nombre del instructor (si aplica)")
        form.addRow("Instructor:", self._edit_instructor)

        self._edit_date = QLineEdit(tp.date_text or "")
        self._edit_date.setPlaceholderText("Fecha del documento")
        form.addRow("Fecha:", self._edit_date)

        # Abstract (if detected)
        if result.abstract:
            self._edit_abstract = QTextEdit()
            self._edit_abstract.setPlainText(result.abstract)
            self._edit_abstract.setMaximumHeight(60)
            # Word count
            wcount = len(result.abstract.split())
            form.addRow(f"Abstract ({wcount} palabras):", self._edit_abstract)
        else:
            self._edit_abstract = None

        # Keywords
        if result.keywords:
            self._edit_keywords = QLineEdit(", ".join(result.keywords))
            form.addRow("Palabras clave:", self._edit_keywords)
        else:
            self._edit_keywords = None

        return box

    # -- Panel 3: Body structure tree --

    def _build_structure_panel(self, result: SemanticDocument) -> QWidget:
        section_count = len(result.body_sections)
        total_words = sum(len(s.content.split()) for s in result.body_sections if s.content)
        box = QGroupBox(f"📋 Estructura ({section_count} secciones • {total_words:,} palabras)")
        box.setStyleSheet(_GROUP_STYLE)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(4, 4, 4, 4)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Sección", "Nivel", "Palabras"])
        tree.setColumnCount(3)
        tree.header().setStretchLastSection(False)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 3):
            tree.header().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        def _add_section_to_tree(
            sec: Section,
            parent_item: QTreeWidgetItem | None,
        ) -> None:
            words = len(sec.content.split()) if sec.content else 0
            item = QTreeWidgetItem(
                [
                    sec.heading or "(sin título)",
                    f"H{sec.level.value}",
                    str(words),
                ]
            )
            if sec.level.value > 1:
                item.setForeground(0, tree.palette().mid().color())
            if parent_item:
                parent_item.addChild(item)
            else:
                tree.addTopLevelItem(item)
            for sub in sec.subsections:
                _add_section_to_tree(sub, item)
            item.setExpanded(True)

        for sec in result.body_sections:
            _add_section_to_tree(sec, None)

        if not result.body_sections:
            empty = QTreeWidgetItem(["(sin secciones detectadas)", "", ""])
            empty.setForeground(0, tree.palette().mid().color())
            tree.addTopLevelItem(empty)

        tree.setStyleSheet("font-size: 9pt;")
        lay.addWidget(tree)
        return box

    # -- Panel 4: References --

    def _build_references_panel(self, result: SemanticDocument) -> QWidget:
        parsed_count = len(result.references_parsed)
        raw_count = len(result.references_raw)
        total = max(parsed_count, raw_count)

        box = QGroupBox(f"📚 Referencias ({parsed_count} parseadas / {raw_count} crudas)")
        box.setStyleSheet(_GROUP_STYLE)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(4, 4, 4, 4)

        if total == 0:
            lbl = QLabel("No se detectaron referencias en el documento.")
            lbl.setStyleSheet("color: #999; font-size: 9pt; padding: 10px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl)
            self._ref_checkboxes = []
            return box

        # Legend
        legend = QLabel("🟢 Parseada (modelo Reference)  •  🟡 Cruda (texto sin parsear)")
        legend.setStyleSheet("font-size: 8pt; color: #666; padding: 2px;")
        lay.addWidget(legend)

        # Show parsed references as primary rows, raw references as fallback
        display_refs: list[tuple[str, str, str, bool]] = []  # (status, type, text, is_parsed)

        for ref in result.references_parsed:
            # Build display text from parsed Reference
            author_str = ""
            if ref.authors:
                names = []
                for a in ref.authors[:3]:
                    names.append(
                        f"{a.last_name}, {a.first_name[0]}." if a.first_name else a.last_name
                    )
                if len(ref.authors) > 3:
                    names.append("et al.")
                author_str = "; ".join(names)
            year_str = str(ref.year) if ref.year else "s.f."
            title_str = ref.title or ""
            text = f"{author_str} ({year_str}). {title_str}"
            display_refs.append(("🟢", ref.ref_type.value, text, True))

        # Add raw references that weren't parsed
        for i, raw in enumerate(result.references_raw):
            if i >= parsed_count:
                display_refs.append(("🟡", "cruda", raw, False))

        rows = len(display_refs)
        self._ref_table = QTableWidget(rows, 4)
        self._ref_table.setHorizontalHeaderLabels(["✓", "Estado", "Tipo", "Referencia"])
        self._ref_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._ref_table.verticalHeader().setVisible(False)
        self._ref_table.setColumnWidth(0, 30)
        self._ref_table.setColumnWidth(1, 30)
        self._ref_table.setColumnWidth(2, 80)
        self._ref_table.setStyleSheet("font-size: 9pt;")

        self._ref_checkboxes: list[QCheckBox] = []

        for row, (status, ref_type, text, _is_parsed) in enumerate(display_refs):
            # Checkbox — default checked for parsed, unchecked for raw
            cb = QCheckBox()
            cb.setChecked(_is_parsed)
            self._ref_checkboxes.append(cb)
            self._ref_table.setCellWidget(row, 0, cb)

            # Status icon
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._ref_table.setItem(row, 1, status_item)

            # Type
            type_item = QTableWidgetItem(ref_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._ref_table.setItem(row, 2, type_item)

            # Text (truncated)
            display_text = text[:140] + "…" if len(text) > 140 else text
            text_item = QTableWidgetItem(display_text)
            text_item.setToolTip(text)
            text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._ref_table.setItem(row, 3, text_item)

        lay.addWidget(self._ref_table)
        return box

    # -- Panel 5: Auto-apply config checkbox --

    def _build_config_checkbox(self) -> QWidget:
        w = QWidget()
        hlay = QHBoxLayout(w)
        hlay.setContentsMargins(4, 4, 4, 4)

        self._auto_apply_config = QCheckBox(
            "Auto-aplicar configuración detectada (idioma, márgenes, fuente)"
        )
        self._auto_apply_config.setChecked(True)
        self._auto_apply_config.setStyleSheet("font-size: 10pt; padding: 4px;")
        hlay.addWidget(self._auto_apply_config)
        hlay.addStretch()

        return w

    # ── Build APADocument from SemanticDocument + user edits ─────────────────

    def accept(self) -> None:
        """Build APADocument from the semantic analysis + user edits."""
        if not self._semantic_doc:
            super().accept()
            return

        sd = self._semantic_doc

        # Title page from editable fields
        title = self._edit_title.text().strip() or "Sin Título"
        authors_raw = self._edit_authors.text().strip()
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()] or ["Autor Desconocido"]
        affiliation = self._edit_affiliation.text().strip() or "Institución"
        course = self._edit_course.text().strip() or None
        instructor = self._edit_instructor.text().strip() or None

        title_page = TitlePage(
            title=title,
            authors=authors,
            affiliation=affiliation,
            course=course,
            instructor=instructor,
        )

        # Abstract
        abstract = None
        if self._edit_abstract:
            abstract = self._edit_abstract.toPlainText().strip() or None

        # Keywords
        keywords: list[str] = []
        if self._edit_keywords:
            kw_text = self._edit_keywords.text().strip()
            keywords = [k.strip() for k in kw_text.split(",") if k.strip()]

        # Body sections — directly from SemanticDocument (already Section objects)
        sections = sd.body_sections

        # References — only checked ones
        from apa_formatter.domain.models.reference import Reference

        references: list[Reference] = []
        if hasattr(self, "_ref_checkboxes") and self._ref_checkboxes:
            parsed = sd.references_parsed
            for i, cb in enumerate(self._ref_checkboxes):
                if cb.isChecked() and i < len(parsed):
                    references.append(parsed[i])

        # Build the final APADocument
        self._result_doc = APADocument(
            title_page=title_page,
            abstract=abstract,
            keywords=keywords,
            sections=sections,
            references=references,
        )

        super().accept()

    def get_document(self) -> APADocument | None:
        """Return the imported document (or None if cancelled)."""
        return self._result_doc

    def auto_apply_config_requested(self) -> bool:
        """Whether the user wants to auto-apply detected config."""
        return hasattr(self, "_auto_apply_config") and self._auto_apply_config.isChecked()

    def get_detected_config(self) -> DetectedConfig | None:
        """Return the auto-detected configuration for application to the profile."""
        if self._semantic_doc:
            return self._semantic_doc.detected_config
        return None


# ---------------------------------------------------------------------------
# Stylesheets
# ---------------------------------------------------------------------------

_BTN_STYLE = """
QPushButton {
    background: #4A90D9;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-size: 10pt;
}
QPushButton:hover { background: #357ABD; }
QPushButton:disabled { background: #CCCCCC; }
"""

_GROUP_STYLE = """
QGroupBox {
    font-weight: bold;
    font-size: 9pt;
    border: 1px solid #DDD;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
}
"""

_DIALOG_STYLE = """
QDialog { background: #FAFAFA; }
QLineEdit, QTextEdit {
    border: 1px solid #CCC;
    border-radius: 3px;
    padding: 4px 6px;
    font-size: 9pt;
    background: white;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #4A90D9;
}
QTableWidget {
    border: 1px solid #DDD;
    border-radius: 3px;
    gridline-color: #EEE;
    background: white;
}
QTableWidget::item {
    padding: 2px 4px;
}
QTreeWidget {
    border: 1px solid #DDD;
    border-radius: 3px;
    background: white;
}
QPushButton {
    background: #4A90D9;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-size: 10pt;
}
QPushButton:hover { background: #357ABD; }
QPushButton:disabled { background: #CCCCCC; }
"""
