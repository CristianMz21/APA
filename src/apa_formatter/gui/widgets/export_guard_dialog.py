"""Smart Export Guard dialog — pre-flight validation results.

Shows the ``ValidationReport`` from ``ExportValidator`` before export,
color-coding errors (blocking) and warnings (dismissible).  The user
can cancel, force-export with warnings, or proceed when clean.

Usage::

    from apa_formatter.gui.widgets.export_guard_dialog import ExportGuardDialog

    dlg = ExportGuardDialog(report, parent=self)
    if dlg.exec() == ExportGuardDialog.DialogCode.Accepted:
        # user chose to export (clean or forced)
        ...
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.gui.theme import Theme
from apa_formatter.validators.export_validator import (
    Severity,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Severity rendering helpers
# ---------------------------------------------------------------------------

_SEVERITY_ICON = {
    Severity.ERROR: "🔴",
    Severity.WARNING: "🟡",
    Severity.INFO: "ℹ️",
}

_SEVERITY_LABEL = {
    Severity.ERROR: "Error",
    Severity.WARNING: "Advertencia",
    Severity.INFO: "Info",
}


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class ExportGuardDialog(QDialog):
    """Pre-flight validation dialog for the Smart Export Guard.

    Shows all issues from a ``ValidationReport``.  When blocking errors
    exist the "Exportar" button is disabled and only "Cancelar" remains.
    When only warnings exist, a "Exportar de todos modos" button appears.
    """

    def __init__(
        self,
        report: ValidationReport,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._report = report
        self.setWindowTitle("🛡️ Verificación Pre-exportación")
        self.setMinimumSize(680, 420)

        layout = QVBoxLayout(self)

        # ── Header / overall status ───────────────────────────────────────
        self._header = QLabel()
        hfont = QFont()
        hfont.setPointSize(13)
        hfont.setBold(True)
        self._header.setFont(hfont)
        self._header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._header)

        # ── Summary counts ────────────────────────────────────────────────
        self._summary = QLabel()
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._summary)

        # ── Issues table ──────────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Nivel", "Código", "Mensaje", "Ubicación"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # ── Button bar ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancel)

        self._btn_force = QPushButton("⚠️ Exportar de todos modos")
        self._btn_force.setToolTip("Exportar ignorando las advertencias (no aplica si hay errores)")
        self._btn_force.clicked.connect(self.accept)
        self._btn_force.setVisible(False)
        btn_row.addWidget(self._btn_force)

        self._btn_export = QPushButton("✅ Exportar")
        self._btn_export.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_export)

        layout.addLayout(btn_row)

        # ── Populate ──────────────────────────────────────────────────────
        self._populate(report)
        self.setStyleSheet(Theme.dialog() + Theme.table())

    # -- Public API ----------------------------------------------------------

    def was_forced(self) -> bool:
        """True if the user clicked 'Export anyway' despite warnings."""
        return (
            self.result() == QDialog.DialogCode.Accepted
            and self._report.warnings
            and not self._report.is_blocking
        )

    # -- Internal ------------------------------------------------------------

    def _populate(self, report: ValidationReport) -> None:
        p = Theme.palette()

        if report.is_clean:
            self._header.setText("✅ Listo para exportar")
            self._header.setStyleSheet(f"color: {p.success}; font-size: 14pt; font-weight: bold;")
            self._summary.setText("No se encontraron problemas.")
            self._summary.setStyleSheet(f"color: {p.text_secondary};")
            self._table.setVisible(False)
            self._btn_force.setVisible(False)
            self._btn_export.setEnabled(True)
            return

        # Counts
        n_errors = len(report.errors)
        n_warnings = len(report.warnings)
        info_issues = [i for i in report.issues if i.severity == Severity.INFO]
        n_info = len(info_issues)

        if report.is_blocking:
            self._header.setText("❌ Errores de exportación encontrados")
            self._header.setStyleSheet(f"color: {p.error}; font-size: 14pt; font-weight: bold;")
            self._btn_export.setEnabled(False)
            self._btn_force.setVisible(False)
        else:
            self._header.setText("⚠️ Advertencias de exportación")
            self._header.setStyleSheet(f"color: {p.warning}; font-size: 14pt; font-weight: bold;")
            self._btn_export.setVisible(False)
            self._btn_force.setVisible(True)

        parts = []
        if n_errors:
            parts.append(f"🔴 {n_errors} error(es)")
        if n_warnings:
            parts.append(f"🟡 {n_warnings} advertencia(s)")
        if n_info:
            parts.append(f"ℹ️ {n_info} info")
        self._summary.setText("  ·  ".join(parts))
        self._summary.setStyleSheet(f"color: {p.text_secondary}; font-size: 10pt;")

        # Fill table
        self._table.setRowCount(len(report.issues))
        for i, issue in enumerate(report.issues):
            severity_text = f"{_SEVERITY_ICON[issue.severity]} {_SEVERITY_LABEL[issue.severity]}"
            self._table.setItem(i, 0, QTableWidgetItem(severity_text))
            self._table.setItem(i, 1, QTableWidgetItem(issue.code.value))
            self._table.setItem(i, 2, QTableWidgetItem(issue.message))
            self._table.setItem(i, 3, QTableWidgetItem(issue.location or "—"))

            # Color-code rows
            row_color = {
                Severity.ERROR: QColor(231, 76, 60, 30),
                Severity.WARNING: QColor(245, 166, 35, 25),
                Severity.INFO: QColor(52, 152, 219, 20),
            }.get(issue.severity)

            if row_color:
                for col in range(4):
                    item = self._table.item(i, col)
                    if item:
                        item.setBackground(row_color)
