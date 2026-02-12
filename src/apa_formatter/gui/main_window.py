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
from PySide6.QtWidgets import (
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
        self.form = DocumentFormWidget()
        self.preview = APAPreviewWidget()

        # --- Layout --------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: structured form
        splitter.addWidget(self.form)

        # Right panel: preview
        splitter.addWidget(self.preview)
        splitter.setSizes([450, 700])

        self.setCentralWidget(splitter)

        # --- Toolbar -------------------------------------------------------
        self._build_toolbar()

        # --- Menu ----------------------------------------------------------
        self._build_menu()

        # --- Status bar ----------------------------------------------------
        self.statusBar().showMessage("Listo — escribe texto y presiona Formatear")

        # --- Styling -------------------------------------------------------
        self.setStyleSheet(_WINDOW_STYLE)

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
        self._profile_label.setStyleSheet("color: #4A90D9; font-weight: bold; font-size: 9pt;")
        tb.addWidget(self._profile_label)

    # ── Menu ──────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        # -- Archivo --
        file_menu = menu_bar.addMenu("&Archivo")

        act_new = file_menu.addAction("Nuevo")
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new)

        act_import = file_menu.addAction("📥 Importar .docx…")
        act_import.setShortcut(QKeySequence("Ctrl+I"))
        act_import.triggered.connect(self._on_import_docx)

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
        self.preview.clear()
        self._current_doc = None
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
        self.statusBar().showMessage(
            f"✅  Formato APA aplicado — {total_words} palabras, "
            f"{len(doc.sections)} sección(es), {len(doc.references)} referencia(s)"
        )

    # ── Export ─────────────────────────────────────────────────────────────

    def _on_export_docx(self) -> None:
        if not self._current_doc:
            self.statusBar().showMessage("⚠️  Formatea primero el documento")
            return

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

    def _on_import_docx(self) -> None:
        from apa_formatter.gui.widgets.import_dialog import ImportDialog

        dlg = ImportDialog(self)
        if dlg.exec() == ImportDialog.DialogCode.Accepted:
            doc = dlg.get_document()
            if doc:
                self.form.set_document(doc)
                self.statusBar().showMessage(
                    f"📥 Importado: {doc.title_page.title} — {len(doc.sections)} sección(es)"
                )

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


# ── Utilities ─────────────────────────────────────────────────────────────


def _label(text: str):
    """Quick QLabel for toolbar."""
    from PySide6.QtWidgets import QLabel

    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight: bold; padding: 0 4px;")
    return lbl


# ── Stylesheet ────────────────────────────────────────────────────────────

_WINDOW_STYLE = """
QMainWindow {
    background-color: #F5F5F5;
}
QToolBar {
    background-color: #ECECEC;
    border-bottom: 1px solid #CCCCCC;
    padding: 4px;
    spacing: 6px;
}
QToolBar QToolButton {
    background-color: #4A90D9;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 11pt;
}
QToolBar QToolButton:hover {
    background-color: #357ABD;
}
QToolBar QToolButton:pressed {
    background-color: #2A5F9E;
}
QComboBox {
    padding: 4px 8px;
    border: 1px solid #BBBBBB;
    border-radius: 3px;
    background: white;
    min-width: 150px;
}
QStatusBar {
    background-color: #ECECEC;
    border-top: 1px solid #CCCCCC;
    font-size: 10pt;
    padding: 2px 8px;
}
QMenuBar {
    background-color: #ECECEC;
    border-bottom: 1px solid #CCCCCC;
}
QMenuBar::item:selected {
    background-color: #4A90D9;
    color: white;
}
"""
