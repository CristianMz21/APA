"""Configuration profile management panel.

Allows switching between APA 7 / SENA profiles, loading custom configs,
viewing the active JSON, and exporting the default config.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.config.loader import load_config

# Built-in profiles
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_PROFILES = {
    "APA 7 (Default)": _CONFIG_DIR / "apa7_default.json",
    "SENA": _CONFIG_DIR / "sena_default.json",
}


class ConfigPanel(QDialog):
    """Dialog for viewing and switching APA configuration profiles."""

    config_changed = Signal(object)  # emits APAConfig

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configuración APA")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # ── Profile selector ──────────────────────────────────────────────
        profile_group = QGroupBox("Perfil de Configuración")
        pg_layout = QVBoxLayout(profile_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Perfil activo:"))
        self._profile_combo = QComboBox()
        for name in _PROFILES:
            self._profile_combo.addItem(name)
        self._profile_combo.addItem("Custom…")
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        row.addWidget(self._profile_combo, stretch=1)
        pg_layout.addLayout(row)

        btn_row = QHBoxLayout()
        btn_load = QPushButton("📂 Cargar Custom…")
        btn_load.clicked.connect(self._on_load_custom)
        btn_export = QPushButton("💾 Exportar Default…")
        btn_export.clicked.connect(self._on_export_default)
        btn_validate = QPushButton("✓ Validar")
        btn_validate.clicked.connect(self._on_validate)
        btn_row.addWidget(btn_load)
        btn_row.addWidget(btn_export)
        btn_row.addWidget(btn_validate)
        btn_row.addStretch()
        pg_layout.addLayout(btn_row)

        layout.addWidget(profile_group)

        # ── JSON viewer ───────────────────────────────────────────────────
        layout.addWidget(QLabel("Configuración activa (JSON):"))
        self._json_view = QPlainTextEdit()
        self._json_view.setReadOnly(True)
        self._json_view.setStyleSheet(
            "font-family: 'Fira Code', 'Consolas', monospace; font-size: 9pt;"
            "background: #FAFAFA; border: 1px solid #DDDDDD;"
        )
        layout.addWidget(self._json_view)

        # ── Status ────────────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setStyleSheet("font-size: 9pt;")
        layout.addWidget(self._status)

        # ── Close ─────────────────────────────────────────────────────────
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        # Load default
        self._current_path = _PROFILES.get("APA 7 (Default)")
        self._load_and_display(self._current_path)

        self.setStyleSheet(_CONFIG_STYLE)

    def _on_profile_changed(self, text: str) -> None:
        if text in _PROFILES:
            self._current_path = _PROFILES[text]
            self._load_and_display(self._current_path)
        elif text == "Custom…":
            self._on_load_custom()

    def _on_load_custom(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Cargar configuración", "", "JSON Files (*.json)"
        )
        if path:
            self._current_path = Path(path)
            self._load_and_display(self._current_path)
            self._profile_combo.setCurrentText("Custom…")

    def _on_export_default(self) -> None:
        dest, _ = QFileDialog.getSaveFileName(
            self, "Exportar configuración", "apa7_config.json", "JSON Files (*.json)"
        )
        if dest:
            default = _PROFILES["APA 7 (Default)"]
            shutil.copy2(default, dest)
            self._status.setText(f"✅ Exportado: {dest}")
            self._status.setStyleSheet("font-size: 9pt; color: #27ae60;")

    def _on_validate(self) -> None:
        if not self._current_path:
            return
        try:
            load_config(self._current_path)
            self._status.setText("✅ Configuración válida")
            self._status.setStyleSheet("font-size: 9pt; color: #27ae60;")
        except Exception as exc:
            self._status.setText(f"❌ Error: {exc}")
            self._status.setStyleSheet("font-size: 9pt; color: #c0392b;")

    def _load_and_display(self, path: Path | None) -> None:
        if not path or not path.exists():
            self._json_view.setPlainText("(archivo no encontrado)")
            return
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            self._json_view.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
            cfg = load_config(path)
            self.config_changed.emit(cfg)
            self._status.setText(f"✅ Perfil cargado: {path.name}")
            self._status.setStyleSheet("font-size: 9pt; color: #27ae60;")
        except Exception as exc:
            self._json_view.setPlainText(f"Error: {exc}")
            self._status.setText(f"❌ {exc}")
            self._status.setStyleSheet("font-size: 9pt; color: #c0392b;")

    def get_config_path(self) -> Path | None:
        return self._current_path


_CONFIG_STYLE = """
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
    padding: 5px 12px;
    font-size: 9pt;
}
QPushButton:hover { background: #357ABD; }
QComboBox {
    padding: 4px 8px;
    border: 1px solid #BBBBBB;
    border-radius: 3px;
    background: white;
    min-width: 150px;
}
"""
