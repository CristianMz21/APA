"""APA 7 compliance checker dialog.

Opens a .docx file and runs APAChecker, displaying results in a table
with a compliance score bar.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class CheckerDialog(QDialog):
    """Dialog that checks a .docx file for APA 7 compliance."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("🔍 Verificar Cumplimiento APA 7")
        self.setMinimumSize(650, 500)

        layout = QVBoxLayout(self)

        # ── File selector ─────────────────────────────────────────────────
        file_row = QHBoxLayout()
        self._path_label = QLabel("Ningún archivo seleccionado")
        self._path_label.setStyleSheet("color: #888; font-style: italic;")
        btn_browse = QPushButton("📂 Seleccionar .docx")
        btn_browse.clicked.connect(self._on_browse)
        file_row.addWidget(self._path_label, stretch=1)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        # ── Score bar ─────────────────────────────────────────────────────
        self._score_bar = QProgressBar()
        self._score_bar.setRange(0, 100)
        self._score_bar.setValue(0)
        self._score_bar.setTextVisible(True)
        self._score_bar.setFormat("Puntaje: %v%")
        self._score_bar.setMinimumHeight(28)
        layout.addWidget(self._score_bar)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self._status_label)

        # ── Results table ─────────────────────────────────────────────────
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Estado", "Regla", "Esperado", "Actual"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        # ── Close button ──────────────────────────────────────────────────
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.setStyleSheet(_CHECKER_STYLE)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir documento .docx", "", "Word Documents (*.docx)"
        )
        if not path:
            return

        self._path_label.setText(path)
        self._path_label.setStyleSheet("color: #333;")
        self._run_check(Path(path))

    def _run_check(self, path: Path) -> None:
        try:
            from apa_formatter.validators.checker import APAChecker

            checker = APAChecker(path)
            report = checker.check()
        except Exception as exc:
            self._status_label.setText(f"❌ Error: {exc}")
            self._status_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #c0392b;")
            return

        # Score bar
        score = report.score
        self._score_bar.setValue(int(score))
        if score >= 80:
            bar_color = "#27ae60"
        elif score >= 60:
            bar_color = "#f39c12"
        else:
            bar_color = "#c0392b"
        self._score_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {bar_color}; }}")

        # Status
        if report.is_compliant:
            self._status_label.setText("✅ CUMPLE — APA 7 Compliant")
            self._status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #27ae60;")
        else:
            self._status_label.setText("❌ NO CUMPLE — Issues Found")
            self._status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #c0392b;")

        # Results table
        results = report.results
        self._table.setRowCount(len(results))
        for i, r in enumerate(results):
            icon = "✅" if r.passed else "❌"
            self._table.setItem(i, 0, QTableWidgetItem(icon))
            self._table.setItem(i, 1, QTableWidgetItem(r.rule_name))
            self._table.setItem(i, 2, QTableWidgetItem(str(r.expected)))
            self._table.setItem(i, 3, QTableWidgetItem(str(r.actual)))

            # Color row
            if not r.passed:
                for col in range(4):
                    item = self._table.item(i, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.transparent)
                        item.setForeground(Qt.GlobalColor.darkRed)


_CHECKER_STYLE = """
QDialog { background: white; }
QTableWidget {
    border: 1px solid #CCCCCC;
    font-size: 10pt;
    gridline-color: #EEEEEE;
}
QHeaderView::section {
    background: #F5F5F5;
    border: 1px solid #DDDDDD;
    padding: 4px;
    font-weight: bold;
    font-size: 9pt;
}
QProgressBar {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    text-align: center;
    font-weight: bold;
    font-size: 11pt;
}
QProgressBar::chunk {
    border-radius: 3px;
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
