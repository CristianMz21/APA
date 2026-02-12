"""Main application window for APA 7 Formatter GUI.

Layout
──────
┌────────────────────────────────────────────────────────────┐
│  Menu bar  (Archivo │ Exportar │ Herramientas │ Ayuda)     │
│  Toolbar   [Fuente ▾] [Variante ▾] [Formatear]            │
├───────────────────────┬────────────────────────────────────┤
│ Document Form         │   Preview APA (output)             │
│ (Tabs: Portada,       │                                    │
│  Resumen, Secciones,  │                                    │
│  Referencias,         │                                    │
│  Apéndices, Opciones) │                                    │
├───────────────────────┴────────────────────────────────────┤
│  Status bar                                                │
└────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence

from apa_formatter.gui.widgets.fixer_report import FixerReportPanel
from apa_formatter.gui.widgets.language_switcher import LanguageSwitcher
from apa_formatter.gui.widgets.navigation_tree import NavigationTree
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar,
)

from apa_formatter.gui.rendering.apa_renderer import render_to_qtextdocument
from apa_formatter.gui.widgets.document_form import DocumentFormWidget
from apa_formatter.gui.widgets.preview import APAPreviewWidget
from apa_formatter.config.loader import load_config
from apa_formatter.config.models import APAConfig
from apa_formatter.domain.models.settings import UserSettings
from apa_formatter.infrastructure.config.settings_manager import SettingsManager
from apa_formatter.models.document import APADocument
from apa_formatter.models.enums import (
    DocumentVariant,
    FontChoice,
)


class APAMainWindow(QMainWindow):
    """Primary window — editor on the left, APA preview on the right."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("APA 7 Formatter")
        self.setMinimumSize(1200, 700)

        # State
        self._current_doc: APADocument | None = None
        self._font_choice = FontChoice.TIMES_NEW_ROMAN
        self._variant = DocumentVariant.STUDENT
        self._active_config: APAConfig = load_config()

        # User preferences (persisted to OS config dir)
        self._settings_manager = SettingsManager()
        self._user_settings: UserSettings = self._settings_manager.load()

        # --- Widgets -------------------------------------------------------
        self.nav_tree = NavigationTree()
        self.form = DocumentFormWidget()
        self.preview = APAPreviewWidget()
        self.fixer_panel = FixerReportPanel()
        self.fixer_panel.setVisible(False)
        self.fixer_panel.accepted.connect(self._on_auto_fix_accept)
        self.fixer_panel.dismissed.connect(self._on_auto_fix_dismiss)

        # --- Layout --------------------------------------------------------
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Navigation tree (left sidebar)
        self._splitter.addWidget(self.nav_tree)

        # Form panel
        self._splitter.addWidget(self.form)

        # Preview panel (center)
        self._splitter.addWidget(self.preview)

        # Fixer report panel (right, hidden by default)
        self._splitter.addWidget(self.fixer_panel)
        self._splitter.setSizes([200, 350, 600, 0])

        self.setCentralWidget(self._splitter)

        # --- Toolbar -------------------------------------------------------
        self._build_toolbar()

        # --- Menu ----------------------------------------------------------
        self._build_menu()

        # --- Status bar ----------------------------------------------------
        self.statusBar().showMessage("Listo — escribe texto y presiona Formatear")

        # --- Styling -------------------------------------------------------
        from apa_formatter.gui.theme import Theme, apply_theme

        qapp = QApplication.instance()
        if qapp:
            apply_theme(qapp)

        self.setStyleSheet(Theme.toolbar() + Theme.splitter())
        self._splitter.setStyleSheet(Theme.splitter())

        # Enable drag & drop for .docx files
        self.setAcceptDrops(True)

        # --- Live preview debounce -----------------------------------------
        self._live_timer = QTimer(self)
        self._live_timer.setSingleShot(True)
        self._live_timer.setInterval(600)  # ms
        self._live_timer.timeout.connect(self._on_live_preview)
        self.form.document_changed.connect(self._live_timer.start)
        self._live_enabled = True

        # --- Sync OpcionesTab with default config --------------------------
        self.form._opciones.set_from_config(self._active_config)
        self.form._opciones.options_changed.connect(self._live_timer.start)

    # ── Toolbar ────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        tb = QToolBar("Herramientas")
        tb.setMovable(False)
        self.addToolBar(tb)

        # Font selector
        tb.addWidget(_label(" Fuente: "))
        self._font_combo = QComboBox()
        self._font_combo.addItems([f.value for f in FontChoice])
        self._font_combo.currentTextChanged.connect(self._on_font_changed)
        tb.addWidget(self._font_combo)

        tb.addSeparator()

        # Variant selector
        tb.addWidget(_label(" Variante: "))
        self._variant_combo = QComboBox()
        self._variant_combo.addItems([v.value.capitalize() for v in DocumentVariant])
        self._variant_combo.currentTextChanged.connect(self._on_variant_changed)
        tb.addWidget(self._variant_combo)

        tb.addSeparator()

        # Format button
        act_format = QAction("📄  Formatear APA", self)
        act_format.setShortcut(QKeySequence("Ctrl+Return"))
        act_format.triggered.connect(self._on_format_clicked)
        tb.addAction(act_format)

        # Auto-fix button
        act_autofix = QAction("✨ Auto-corregir", self)
        act_autofix.setShortcut(QKeySequence("Ctrl+Shift+A"))
        act_autofix.setToolTip("Ejecutar auto-corrección APA en el texto actual")
        act_autofix.triggered.connect(self._on_auto_fix)
        tb.addAction(act_autofix)

        tb.addSeparator()

        # Live preview toggle
        self._live_cb = QCheckBox("Vista previa en vivo")
        self._live_cb.setChecked(True)
        self._live_cb.setToolTip("Actualizar vista previa automáticamente")
        self._live_cb.toggled.connect(self._on_live_toggled)
        tb.addWidget(self._live_cb)

        tb.addSeparator()

        # Active profile label
        self._profile_label = _label(" Perfil: APA 7 ")
        self._profile_label.setToolTip("Perfil de configuración activo")
        tb.addWidget(self._profile_label)

        tb.addSeparator()

        # Language switcher
        self._lang_switcher = LanguageSwitcher()
        self._lang_switcher.language_changed.connect(self._on_language_changed)
        tb.addWidget(self._lang_switcher)

    # ── Menu ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # -- Archivo --
        file_menu = menu_bar.addMenu("&Archivo")

        act_new = file_menu.addAction("Nuevo")
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new)

        act_import = file_menu.addAction("📥 Importar documento…")
        act_import.setShortcut(QKeySequence("Ctrl+I"))
        act_import.triggered.connect(self._on_import_file)

        file_menu.addSeparator()

        act_quit = file_menu.addAction("Salir")
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)

        # -- Exportar --
        export_menu = menu_bar.addMenu("&Exportar")

        act_docx = export_menu.addAction("Exportar a Word (.docx)")
        act_docx.setShortcut(QKeySequence("Ctrl+Shift+W"))
        act_docx.triggered.connect(self._on_export_docx)

        act_pdf = export_menu.addAction("Exportar a PDF (.pdf)")
        act_pdf.setShortcut(QKeySequence("Ctrl+Shift+P"))
        act_pdf.triggered.connect(self._on_export_pdf)

        # -- Herramientas --
        tools_menu = menu_bar.addMenu("&Herramientas")

        act_check = tools_menu.addAction("🔍 Verificar APA (.docx)…")
        act_check.setShortcut(QKeySequence("Ctrl+Shift+C"))
        act_check.triggered.connect(self._on_check_apa)

        act_config = tools_menu.addAction("⚙️ Configuración…")
        act_config.triggered.connect(self._on_config)

        act_settings = tools_menu.addAction("🔧 Preferencias…")
        act_settings.triggered.connect(self._on_settings)

        act_info = tools_menu.addAction("ℹ️ Info y Demo…")
        act_info.triggered.connect(self._on_info_demo)

        # -- Ayuda --
        help_menu = menu_bar.addMenu("A&yuda")
        act_about = help_menu.addAction("Acerca de...")
        act_about.triggered.connect(self._on_about)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_language_changed(self, lang_code: str) -> None:
        """Switch application locale."""
        from apa_formatter.locale import get_locale

        locale = get_locale(lang_code)
        self._current_locale = locale
        self.statusBar().showMessage(f"🌐 Idioma: {locale.name}")

    def _on_live_toggled(self, checked: bool) -> None:
        self._live_enabled = checked
        if checked:
            # Immediately re-render when enabling
            self._on_live_preview()

    def _on_live_preview(self) -> None:
        """Debounced live preview — silently rebuild + render."""
        if not self._live_enabled:
            return
        try:
            doc = self.form.build_document(
                font=self._font_choice,
                variant=self._variant,
            )
            self._current_doc = doc
            qt_doc = render_to_qtextdocument(self._current_doc)
            self.preview.show_document(qt_doc)
        except Exception:
            pass  # Silently ignore incomplete form data

    def _on_font_changed(self, text: str) -> None:
        try:
            self._font_choice = FontChoice(text)
        except ValueError:
            pass

    def _on_variant_changed(self, text: str) -> None:
        try:
            self._variant = DocumentVariant(text.lower())
        except ValueError:
            pass

    def _on_new(self) -> None:
        self.form.clear()
        self._current_doc = None
        self.nav_tree.clear()
        # Reset preview with empty document
        from PySide6.QtGui import QTextDocument

        self.preview.show_document(QTextDocument())
        self.preview.set_document_stats()
        self.statusBar().showMessage("Nuevo documento")

    def _on_format_clicked(self) -> None:
        # Build APADocument from structured form fields
        try:
            doc = self.form.build_document(
                font=self._font_choice,
                variant=self._variant,
            )
        except Exception as exc:
            self.statusBar().showMessage(f"⚠️  Error al crear documento: {exc}")
            return

        self._current_doc = doc

        qt_doc = render_to_qtextdocument(self._current_doc)
        self.preview.show_document(qt_doc)

        # Count words across all section content
        total_words = sum(len(s.content.split()) for s in doc.sections if s.content)
        if doc.abstract:
            total_words += len(doc.abstract.split())

        # Feed stats to the preview status bar
        self.preview.set_document_stats(
            word_count=total_words,
            section_count=len(doc.sections),
            ref_count=len(doc.references),
            font_name=self._font_choice.value,
        )

        self.statusBar().showMessage(
            f"✅  Formato APA aplicado — {total_words} palabras, "
            f"{len(doc.sections)} sección(es), {len(doc.references)} referencia(s)"
        )

        # Update navigation tree
        self.nav_tree.set_document(doc)

    # ── Auto-Fix ──────────────────────────────────────────────────────────

    def _on_auto_fix(self) -> None:
        """Run the APAAutoFormatter pipeline on all section text."""
        # Gather text from all sections
        sections_text = []
        for i in range(self.form._sections_list.count()):
            item = self.form._sections_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data.get("content"):
                sections_text.append(data["content"])

        full_text = "\n\n".join(sections_text)
        if not full_text.strip():
            self.statusBar().showMessage("⚠️  Escribe texto primero")
            return

        # Import and run the pipeline in a background thread
        from apa_formatter.automation.pipeline import APAAutoFormatter
        from apa_formatter.gui.widgets.async_overlay import AsyncOverlay, AsyncWorker

        formatter = APAAutoFormatter()
        worker = AsyncWorker(formatter.run, full_text)

        self._autofix_overlay = AsyncOverlay(self, "Analizando texto…")
        self._autofix_overlay.run(worker)

        worker.finished.connect(self._on_auto_fix_done)
        worker.error.connect(self._on_auto_fix_error)

        self.statusBar().showMessage("✨ Ejecutando auto-corrección…")

    def _on_auto_fix_done(self, result) -> None:
        """Handle auto-fix completion."""
        from apa_formatter.automation.base import FixResult

        if not isinstance(result, FixResult):
            return

        self._autofix_result = result

        # Show fixer panel with results
        self.fixer_panel.show_result(result)
        self.fixer_panel.setVisible(True)
        # Adjust splitter to show the panel (4-pane: nav, form, preview, fixer)
        self._splitter.setSizes([200, 250, 450, 300])

        n = result.total_fixes
        self.statusBar().showMessage(
            f"✨ Auto-corrección completada: {n} corrección{'es' if n != 1 else ''} encontrada{'s' if n != 1 else ''}"
        )

    def _on_auto_fix_error(self, exc) -> None:
        """Handle auto-fix error."""
        self.statusBar().showMessage(f"❌ Error en auto-corrección: {exc}")

    def _on_auto_fix_accept(self) -> None:
        """User accepted all auto-corrections — apply corrected text."""
        result = self.fixer_panel.get_result()
        if result and result.text:
            # Apply the corrected text back to the first section
            # (In a future version, map corrections to individual sections)
            if self.form._sections_list.count() > 0:
                item = self.form._sections_list.item(0)
                data = item.data(Qt.ItemDataRole.UserRole) or {}
                data["content"] = result.text
                item.setData(Qt.ItemDataRole.UserRole, data)

            self.statusBar().showMessage(f"✅ {result.total_fixes} correcciones aplicadas")

        # Re-trigger live preview
        if self._live_enabled:
            self._on_live_preview()

    def _on_auto_fix_dismiss(self) -> None:
        """User dismissed the auto-fix results."""
        self.fixer_panel.setVisible(False)
        self._splitter.setSizes([200, 350, 600, 0])
        self.statusBar().showMessage("Correcciones descartadas")

    # ── Export ─────────────────────────────────────────────────────────────

    # ── Semantic bridge (APADocument → SemanticDocument) ────────────────

    def _build_semantic_doc(self):  # -> SemanticDocument
        """Convert the current APADocument into a SemanticDocument for validation."""
        from apa_formatter.models.semantic_document import (
            SemanticDocument,
            TitlePageData,
        )

        doc = self._current_doc
        tp = doc.title_page

        title_data = TitlePageData(
            title=tp.title,
            authors=list(tp.authors),
            affiliation=tp.affiliation or None,
            course=tp.course,
            instructor=tp.instructor,
        )

        # Map APADocument sections → SemanticDocument body_sections
        from apa_formatter.domain.models.document import Section as DomainSection

        body_sections = [
            DomainSection(
                heading=s.heading,
                content=s.content,
                level=s.level,
                subsections=list(s.subsections),
            )
            for s in doc.sections
        ]

        return SemanticDocument(
            title_page=title_data,
            abstract=doc.abstract,
            body_sections=body_sections,
            references_parsed=list(doc.references),
        )

    def _run_export_guard(self) -> bool:
        """Run pre-flight validation; return True if export should proceed."""
        from apa_formatter.validators.export_validator import ExportValidator
        from apa_formatter.gui.widgets.export_guard_dialog import ExportGuardDialog

        try:
            sem_doc = self._build_semantic_doc()
        except Exception:
            # If we can't build a SemanticDocument, skip validation
            return True

        validator = ExportValidator()
        report = validator.validate(sem_doc)

        if report.is_clean:
            return True

        dlg = ExportGuardDialog(report, parent=self)
        return dlg.exec() == ExportGuardDialog.DialogCode.Accepted

    def _on_export_docx(self) -> None:
        if not self._current_doc:
            self.statusBar().showMessage("⚠️  Formatea primero el documento")
            return

        # 1. Export Guard
        if not self._run_export_guard():
            self.statusBar().showMessage("🛡️  Exportación cancelada por la verificación")
            return

        # 2. AI Correction Prompt
        if self._ask_ai_correction():
            self._run_ai_correction(on_done=self._do_export_docx)
        else:
            self._do_export_docx()

    def _do_export_docx(self) -> None:
        """Perform the actual DOCX export (file dialog + generation)."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar a Word",
            "documento_apa.docx",
            "Word Documents (*.docx)",
        )
        if not path:
            return

        try:
            from apa_formatter.adapters.docx_adapter import DocxAdapter

            adapter = DocxAdapter(
                self._current_doc,
                config=self._build_effective_config(),
                user_settings=self._user_settings,
            )
            adapter.generate(Path(path))
            self.statusBar().showMessage(f"✅  Exportado: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error de exportación", str(exc))

    def _on_export_pdf(self) -> None:
        if not self._current_doc:
            self.statusBar().showMessage("⚠️  Formatea primero el documento")
            return

        if not self._run_export_guard():
            self.statusBar().showMessage("🛡️  Exportación cancelada por la verificación")
            return

        # 2. AI Correction Prompt
        if self._ask_ai_correction():
            self._run_ai_correction(on_done=self._do_export_pdf)
        else:
            self._do_export_pdf()

    def _do_export_pdf(self) -> None:
        """Perform the actual PDF export."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar a PDF",
            "documento_apa.pdf",
            "PDF Documents (*.pdf)",
        )
        if not path:
            return

        try:
            from apa_formatter.adapters.pdf_adapter import PdfAdapter

            adapter = PdfAdapter(
                self._current_doc,
                config=self._build_effective_config(),
                user_settings=self._user_settings,
            )
            adapter.generate(Path(path))
            self.statusBar().showMessage(f"✅  Exportado: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error de exportación", str(exc))

    def _ask_ai_correction(self) -> bool:
        """Ask user if they want to run AI correction."""
        reply = QMessageBox.question(
            self,
            "Mejora con IA",
            "¿Desea que la IA revise y corrija el documento antes de exportar?\n\n"
            "Esto verificará el título (Title Case), resumen y palabras clave.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _run_ai_correction(self, on_done) -> None:
        """Execute AI correction pipeline asynchronously."""
        try:
            from apa_formatter.infrastructure.ai.gemini_client import GeminiClient
            from apa_formatter.infrastructure.ai.corrector import AiCorrector
            from apa_formatter.gui.widgets.async_overlay import AsyncOverlay, AsyncWorker

            # 1. Init Client
            try:
                client = GeminiClient()
            except ValueError:
                QMessageBox.warning(
                    self,
                    "API Key faltante",
                    "No se encontró la clave de API de Gemini (GEMINI_API_KEY).\n"
                    "Configure la variable de entorno o use el archivo .env.",
                )
                on_done()
                return

            corrector = AiCorrector(client)

            # 2. Worker
            def _bk_task():
                return corrector.correct_document(self._current_doc)

            worker = AsyncWorker(_bk_task)
            overlay = AsyncOverlay(self, "IA analizando y corrigiendo...")

            # 3. Completion Handler
            def _on_finished(report):
                changes = report.get("changes", [])
                if changes:
                    msg = "Correcciones realizadas:\n\n" + "\n".join(f"• {c}" for c in changes)
                    QMessageBox.information(self, "IA Completada", msg)

                    # Update UI
                    self.form.set_document(self._current_doc)
                    if self._live_enabled:
                        self._on_live_preview()
                else:
                    self.statusBar().showMessage("✨ La IA no encontró problemas.")

                # Proceed to actual export
                on_done()

            def _on_error(exc):
                QMessageBox.warning(self, "Error AI", str(exc))
                on_done()

            worker.finished.connect(_on_finished)
            worker.error.connect(_on_error)

            overlay.run(worker)
            self._ai_overlay = overlay  # keep ref

        except ImportError:
            QMessageBox.warning(
                self, "Falta librería", "Instale el soporte AI: pip install 'apa-formatter[ai]'"
            )
            on_done()
        except Exception as e:
            QMessageBox.warning(self, "Error AI", str(e))
            on_done()

    # ── Phase 3: APA Checker ──────────────────────────────────────────────

    def _on_check_apa(self) -> None:
        from apa_formatter.gui.widgets.checker_dialog import CheckerDialog

        dlg = CheckerDialog(self)
        dlg.exec()

    # ── Phase 4: Config Management ────────────────────────────────────────

    def _on_config(self) -> None:
        from apa_formatter.gui.widgets.config_panel import ConfigPanel

        dlg = ConfigPanel(self)
        dlg.config_changed.connect(self._on_config_changed)
        dlg.exec()

    def _on_settings(self) -> None:
        from apa_formatter.gui.widgets.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._settings_manager, parent=self)
        dlg.settings_changed.connect(self._on_settings_changed)
        dlg.exec()

    def _on_settings_changed(self, settings: UserSettings) -> None:
        self._user_settings = settings
        self.statusBar().showMessage("✅  Preferencias actualizadas")
        # Refresh live preview with new settings
        if self._live_enabled:
            self._on_live_preview()

    def _on_config_changed(self, config: APAConfig) -> None:
        self._active_config = config
        # Sync options tab with new profile values
        self.form._opciones.set_from_config(config)
        # Update profile label
        name = "Custom"
        if config.metadatos_norma:
            name = config.metadatos_norma.institucion
        elif config.metadata.norma == "APA":
            name = f"APA {config.metadata.edicion}"
        self._profile_label.setText(f" Perfil: {name} ")
        self.statusBar().showMessage(f"✅  Perfil cambiado: {name}")

    def _build_effective_config(self) -> APAConfig:
        """Merge OpcionesTab overrides into the active config profile."""
        opts = self.form._opciones.get_options()
        data = self._active_config.model_dump()

        # Page margins
        data["configuracion_pagina"]["margenes"]["superior_cm"] = opts["margin_top_cm"]
        data["configuracion_pagina"]["margenes"]["inferior_cm"] = opts["margin_bottom_cm"]
        data["configuracion_pagina"]["margenes"]["izquierda_cm"] = opts["margin_left_cm"]
        data["configuracion_pagina"]["margenes"]["derecha_cm"] = opts["margin_right_cm"]

        if opts["binding_enabled"]:
            data["configuracion_pagina"]["margenes"]["condicion_empaste"] = {
                "descripcion": "Empaste habilitado",
                "izquierda_cm": opts["binding_left_cm"],
            }
        else:
            data["configuracion_pagina"]["margenes"]["condicion_empaste"] = None

        # Text format
        data["formato_texto"]["alineacion"] = opts["alignment"]
        data["formato_texto"]["justificado"] = opts["alignment"] == "justificado"
        data["formato_texto"]["interlineado_general"] = opts["line_spacing"]
        data["formato_texto"]["sangria_parrafo"]["medida_cm"] = opts["indent_cm"]
        data["formato_texto"]["espaciado_parrafos"]["anterior_pt"] = opts["space_before_pt"]
        data["formato_texto"]["espaciado_parrafos"]["posterior_pt"] = opts["space_after_pt"]

        return APAConfig.model_validate(data)

    # ── Phase 5: DOCX Import ──────────────────────────────────────────────

    def _on_import_file(self) -> None:
        from apa_formatter.gui.widgets.import_dialog import ImportDialog

        dlg = ImportDialog(self)
        if dlg.exec() == ImportDialog.DialogCode.Accepted:
            doc = dlg.get_document()
            if doc:
                self.form.set_document(doc)

                # Auto-apply detected config if requested
                if dlg.auto_apply_config_requested():
                    detected = dlg.get_detected_config()
                    if detected:
                        self._apply_detected_config(detected)

                self.statusBar().showMessage(
                    f"📥 Importado: {doc.title_page.title} — "
                    f"{len(doc.sections)} sección(es), "
                    f"{len(doc.references)} referencia(s)"
                )

    def _import_file(self, path: Path) -> None:
        """Import a .docx or .pdf file directly (used by drag & drop)."""
        from apa_formatter.gui.widgets.import_dialog import ImportDialog

        dlg = ImportDialog(self, filepath=path)
        if dlg.exec() == ImportDialog.DialogCode.Accepted:
            doc = dlg.get_document()
            if doc:
                self.form.set_document(doc)
                if dlg.auto_apply_config_requested():
                    detected = dlg.get_detected_config()
                    if detected:
                        self._apply_detected_config(detected)
                self.statusBar().showMessage(f"📥 Importado (drag & drop): {doc.title_page.title}")

    def _apply_detected_config(self, detected) -> None:
        """Apply auto-detected config values to the current options."""
        opts = self.form._opciones.get_options()

        if detected.line_spacing is not None:
            opts["line_spacing"] = detected.line_spacing

        if detected.detected_fonts:
            # Update font choice if we recognize a known font
            font_name = detected.detected_fonts[0].lower()
            if "times" in font_name:
                from apa_formatter.models.enums import FontChoice

                self._font_choice = FontChoice.TIMES_NEW_ROMAN
            elif "arial" in font_name or "calibri" in font_name:
                from apa_formatter.models.enums import FontChoice

                self._font_choice = FontChoice.ARIAL

        self.form._opciones.set_options(opts)

    # ── Phase 6: Info & Demo ──────────────────────────────────────────────

    def _on_info_demo(self) -> None:
        from apa_formatter.gui.widgets.info_panel import InfoDemoDialog

        dlg = InfoDemoDialog(self)
        dlg.exec()

    # ── About ─────────────────────────────────────────────────────────────

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "APA 7 Formatter",
            "<h2>APA 7 Formatter</h2>"
            "<p>Formateador de documentos conforme a normas APA 7ª edición.</p>"
            "<p>Licencia MIT — Open Source</p>"
            "<p><b>Stack:</b> Python + PySide6 (Qt 6)</p>"
            "<p><b>Features:</b> Editor, Referencias, Check, Config, Import, Demo</p>",
        )

    # ── Drag & Drop .docx / .pdf ──────────────────────────────────────────

    _IMPORT_EXTENSIONS = (".docx", ".pdf")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept drag if it contains a .docx or .pdf file."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(self._IMPORT_EXTENSIONS):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        """Import the first supported file dropped onto the window."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(self._IMPORT_EXTENSIONS):
                self._import_file(Path(path))
                event.acceptProposedAction()
                return
        event.ignore()


# ── Utilities ─────────────────────────────────────────────────────────────


def _label(text: str):
    """Quick QLabel for toolbar."""
    from PySide6.QtWidgets import QLabel

    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight: bold; padding: 0 4px;")
    return lbl
