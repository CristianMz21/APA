"""Settings dialog — user preferences panel.

Auto-generates controls (checkboxes, combos, spinners) from the
``UserSettings`` Pydantic model.  Emits ``settings_changed`` on Apply
so that the main window can refresh the live preview.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.domain.models.enums import ExportFormat, FontFamily, Language
from apa_formatter.domain.models.settings import UserSettings
from apa_formatter.infrastructure.config.settings_manager import SettingsManager


class SettingsDialog(QDialog):
    """Modal dialog for editing user preferences.

    Emits :pyqtSignal:`settings_changed` with the new ``UserSettings``
    whenever the user clicks **Aplicar**.
    """

    settings_changed = Signal(object)  # emits UserSettings

    def __init__(
        self,
        settings_manager: SettingsManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("🔧 Preferencias")
        self.setMinimumSize(480, 420)

        self._manager = settings_manager
        self._settings = self._manager.load()

        layout = QVBoxLayout(self)

        # ── Document Structure ────────────────────────────────────────
        doc_group = QGroupBox("Estructura del Documento")
        doc_layout = QVBoxLayout(doc_group)

        self._chk_title_break = QCheckBox("Salto de página después de portada")
        self._chk_title_break.setChecked(self._settings.document.force_title_page_break)
        doc_layout.addWidget(self._chk_title_break)

        self._chk_abstract = QCheckBox("Incluir sección de resumen")
        self._chk_abstract.setChecked(self._settings.document.include_abstract)
        doc_layout.addWidget(self._chk_abstract)

        self._chk_student = QCheckBox("Modo Estudiante (sin Running Head)")
        self._chk_student.setChecked(self._settings.document.student_mode)
        doc_layout.addWidget(self._chk_student)

        layout.addWidget(doc_group)

        # ── Formatting ────────────────────────────────────────────────
        fmt_group = QGroupBox("Formato")
        fmt_layout = QVBoxLayout(fmt_group)

        # Font family
        row_font = QHBoxLayout()
        row_font.addWidget(QLabel("Fuente:"))
        self._combo_font = QComboBox()
        for ff in FontFamily:
            self._combo_font.addItem(ff.value, ff)
        self._combo_font.setCurrentText(self._settings.formatting.font_family.value)
        row_font.addWidget(self._combo_font, stretch=1)
        fmt_layout.addLayout(row_font)

        # Font size
        row_size = QHBoxLayout()
        row_size.addWidget(QLabel("Tamaño (pt):"))
        self._spin_size = QSpinBox()
        self._spin_size.setRange(8, 24)
        self._spin_size.setValue(self._settings.formatting.font_size)
        row_size.addWidget(self._spin_size, stretch=1)
        fmt_layout.addLayout(row_size)

        # Line spacing
        row_spacing = QHBoxLayout()
        row_spacing.addWidget(QLabel("Interlineado:"))
        self._spin_spacing = QDoubleSpinBox()
        self._spin_spacing.setRange(1.0, 3.0)
        self._spin_spacing.setSingleStep(0.15)
        self._spin_spacing.setDecimals(2)
        self._spin_spacing.setValue(self._settings.formatting.line_spacing)
        row_spacing.addWidget(self._spin_spacing, stretch=1)
        fmt_layout.addLayout(row_spacing)

        layout.addWidget(fmt_group)

        # ── System ────────────────────────────────────────────────────
        sys_group = QGroupBox("Sistema")
        sys_layout = QVBoxLayout(sys_group)

        row_lang = QHBoxLayout()
        row_lang.addWidget(QLabel("Idioma:"))
        self._combo_lang = QComboBox()
        self._combo_lang.addItem("Español", Language.ES)
        self._combo_lang.addItem("English", Language.EN)
        self._combo_lang.setCurrentText(
            "Español" if self._settings.system.language == Language.ES else "English"
        )
        row_lang.addWidget(self._combo_lang, stretch=1)
        sys_layout.addLayout(row_lang)

        row_export = QHBoxLayout()
        row_export.addWidget(QLabel("Exportar por defecto:"))
        self._combo_export = QComboBox()
        for ef in ExportFormat:
            self._combo_export.addItem(ef.value.upper(), ef)
        self._combo_export.setCurrentText(self._settings.system.default_export_format.value.upper())
        row_export.addWidget(self._combo_export, stretch=1)
        sys_layout.addLayout(row_export)

        layout.addWidget(sys_group)

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        btn_reset = QPushButton("↺ Restaurar Defaults")
        btn_reset.clicked.connect(self._on_reset)
        btn_row.addWidget(btn_reset)

        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_apply = QPushButton("✓ Aplicar")
        btn_apply.setDefault(True)
        btn_apply.clicked.connect(self._on_apply)
        btn_row.addWidget(btn_apply)

        layout.addLayout(btn_row)

        self.setStyleSheet(_SETTINGS_STYLE)

    # -- Slots ---------------------------------------------------------------

    def _build_settings_from_ui(self) -> UserSettings:
        """Read all widget values and produce a ``UserSettings``."""
        return UserSettings.model_validate(
            {
                "document": {
                    "force_title_page_break": self._chk_title_break.isChecked(),
                    "include_abstract": self._chk_abstract.isChecked(),
                    "student_mode": self._chk_student.isChecked(),
                },
                "formatting": {
                    "font_family": self._combo_font.currentData().value,
                    "font_size": self._spin_size.value(),
                    "line_spacing": self._spin_spacing.value(),
                },
                "system": {
                    "language": self._combo_lang.currentData().value,
                    "default_export_format": self._combo_export.currentData().value,
                },
            }
        )

    def _populate_ui(self, settings: UserSettings) -> None:
        """Populate all widgets from a ``UserSettings`` instance."""
        self._chk_title_break.setChecked(settings.document.force_title_page_break)
        self._chk_abstract.setChecked(settings.document.include_abstract)
        self._chk_student.setChecked(settings.document.student_mode)

        self._combo_font.setCurrentText(settings.formatting.font_family.value)
        self._spin_size.setValue(settings.formatting.font_size)
        self._spin_spacing.setValue(settings.formatting.line_spacing)

        self._combo_lang.setCurrentText(
            "Español" if settings.system.language == Language.ES else "English"
        )
        self._combo_export.setCurrentText(settings.system.default_export_format.value.upper())

    def _on_apply(self) -> None:
        """Save settings and emit the change signal."""
        self._settings = self._build_settings_from_ui()
        self._manager.save(self._settings)
        self.settings_changed.emit(self._settings)
        self.accept()

    def _on_reset(self) -> None:
        """Reset all preferences to factory defaults."""
        reply = QMessageBox.question(
            self,
            "Restaurar Defaults",
            "¿Seguro que deseas restaurar las preferencias por defecto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings = self._manager.reset_to_defaults()
            self._populate_ui(self._settings)


# ── Stylesheet ────────────────────────────────────────────────────────────

_SETTINGS_STYLE = """
QDialog { background: white; }
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
QPushButton {
    background: #4A90D9;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-size: 9pt;
}
QPushButton:hover { background: #357ABD; }
QComboBox, QSpinBox, QDoubleSpinBox {
    padding: 4px 8px;
    border: 1px solid #BBBBBB;
    border-radius: 3px;
    background: white;
    min-width: 120px;
}
QCheckBox { font-size: 10pt; padding: 3px 0; }
"""
