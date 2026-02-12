"""Info panel and demo document generator.

Combines the APA info command (showing configuration details) and the
demo command (generating an example APA 7 document) into a single dialog.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.config.loader import get_config
from apa_formatter.models.enums import FontChoice, OutputFormat


class InfoDemoDialog(QDialog):
    """Dialog showing APA config info and providing demo document generation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ℹ️ Información APA 7 y Demo")
        self.setMinimumSize(600, 550)

        layout = QVBoxLayout(self)

        # ── Info Section ──────────────────────────────────────────────────
        info_group = QGroupBox("Información de Configuración")
        info_layout = QVBoxLayout(info_group)
        self._info_text = QTextEdit()
        self._info_text.setReadOnly(True)
        self._info_text.setStyleSheet(
            "font-family: monospace; font-size: 9pt;background: #F9F9F9; border: 1px solid #DDDDDD;"
        )
        info_layout.addWidget(self._info_text)
        layout.addWidget(info_group)

        self._populate_info()

        # ── Demo Section ──────────────────────────────────────────────────
        demo_group = QGroupBox("Generar Documento Demo")
        demo_layout = QVBoxLayout(demo_group)

        demo_desc = QLabel(
            "Genera un documento APA 7 de ejemplo completo con portada, resumen,\n"
            "secciones con múltiples niveles de encabezado, referencias y apéndice."
        )
        demo_desc.setWordWrap(True)
        demo_desc.setStyleSheet("font-size: 10pt; margin-bottom: 6px;")
        demo_layout.addWidget(demo_desc)

        btn_row = QHBoxLayout()
        btn_demo_docx = QPushButton("📄 Demo .docx")
        btn_demo_docx.clicked.connect(lambda: self._generate_demo(OutputFormat.DOCX))
        btn_demo_pdf = QPushButton("📕 Demo .pdf")
        btn_demo_pdf.clicked.connect(lambda: self._generate_demo(OutputFormat.PDF))
        btn_row.addWidget(btn_demo_docx)
        btn_row.addWidget(btn_demo_pdf)
        btn_row.addStretch()
        demo_layout.addLayout(btn_row)

        self._demo_status = QLabel("")
        self._demo_status.setStyleSheet("font-size: 9pt;")
        demo_layout.addWidget(self._demo_status)

        layout.addWidget(demo_group)

        # ── Close ─────────────────────────────────────────────────────────
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.setStyleSheet(_INFO_STYLE)

    def _populate_info(self) -> None:
        try:
            cfg = get_config()
            lines = [
                "═══ Configuración APA 7 Activa ═══\n",
                f"📐 Márgenes:      {cfg.page.margins.top}″ (todos los lados)",
                f"📏 Interlineado:  {cfg.text.line_spacing}",
                f"📝 Sangría:       {cfg.text.first_line_indent}″ primera línea",
                f"📖 Tamaño fuente: {cfg.text.font_size}pt",
                "",
                "── Fuentes disponibles ──",
            ]
            for font in FontChoice:
                lines.append(f"  • {font.value}")
            lines.extend(
                [
                    "",
                    "── Niveles de encabezado ──",
                ]
            )
            for level in cfg.headings:
                hcfg = cfg.headings[level]
                lines.append(
                    f"  {level}: "
                    f"{'bold' if hcfg.bold else ''} "
                    f"{'italic' if hcfg.italic else ''} "
                    f"align={hcfg.alignment}"
                )
            self._info_text.setPlainText("\n".join(lines))
        except Exception as exc:
            self._info_text.setPlainText(f"Error cargando configuración: {exc}")

    def _generate_demo(self, fmt: OutputFormat) -> None:
        ext = ".docx" if fmt == OutputFormat.DOCX else ".pdf"
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Demo",
            f"demo_apa7{ext}",
            f"{'Word' if fmt == OutputFormat.DOCX else 'PDF'} (*{ext})",
        )
        if not dest:
            return

        try:
            from apa_formatter.cli import _build_demo_document, _generate_document

            doc = _build_demo_document(FontChoice.TIMES_NEW_ROMAN, fmt)
            cfg = get_config()
            result = _generate_document(doc, Path(dest), cfg)
            self._demo_status.setText(f"✅ Demo generado: {result}")
            self._demo_status.setStyleSheet("font-size: 9pt; color: #27ae60;")
        except Exception as exc:
            self._demo_status.setText(f"❌ Error: {exc}")
            self._demo_status.setStyleSheet("font-size: 9pt; color: #c0392b;")


_INFO_STYLE = """
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
    font-size: 10pt;
}
QPushButton:hover { background: #357ABD; }
"""
