"""APA Preview widget — page-canvas viewer with zoom and status bar.

Renders the APA-formatted QTextDocument inside a visual "paper page"
with shadow, margins indicator, zoom controls, and a word/page counter.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QTextDocument,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_ZOOM = 50
_MAX_ZOOM = 200
_DEFAULT_ZOOM = 100
_ZOOM_STEP = 10


# ---------------------------------------------------------------------------
# Page-canvas text viewer
# ---------------------------------------------------------------------------


class _PageCanvas(QTextEdit):
    """QTextEdit subclass that draws a page shadow and margin guides."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Page appearance
        self._page_shadow_color = QColor(0, 0, 0, 30)
        self._page_border_color = QColor(200, 200, 200)
        self._margin_guide_color = QColor(220, 230, 245, 60)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Draw page background with shadow before rendering text."""
        super().paintEvent(event)

        # Draw margin guides as subtle blue tinted lines
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Margin guide overlay (subtle APA 2.54cm margin indicator)
        vp = self.viewport().rect()
        margin_px = int(vp.width() * 0.08)  # ~2.54cm proportional hint

        pen = QPen(self._margin_guide_color, 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)

        # Left margin
        if margin_px > 10:
            painter.drawLine(margin_px, 0, margin_px, vp.height())
            # Right margin
            painter.drawLine(vp.width() - margin_px, 0, vp.width() - margin_px, vp.height())

        painter.end()


# ---------------------------------------------------------------------------
# Public widget — preview panel with zoom and status
# ---------------------------------------------------------------------------


class APAPreviewWidget(QWidget):
    """APA preview panel: page canvas + zoom bar + status bar."""

    zoom_changed = Signal(int)  # zoom percentage

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._zoom = _DEFAULT_ZOOM
        self._doc: QTextDocument | None = None
        self._word_count = 0
        self._section_count = 0
        self._ref_count = 0
        self._font_name = "Times New Roman"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Page canvas (main area) ─────────────────────────────────────────
        self._canvas = _PageCanvas()
        self._canvas.setStyleSheet("""
            _PageCanvas, QTextEdit {
                background-color: #E8E8E8;
                selection-background-color: #4A90D9;
                selection-color: white;
            }
        """)
        layout.addWidget(self._canvas, stretch=1)

        # ── Zoom bar ────────────────────────────────────────────────────────
        zoom_bar = QWidget()
        zoom_bar.setFixedHeight(32)
        zoom_bar.setStyleSheet("""
            QWidget {
                background: #F0F0F0;
                border-top: 1px solid #D0D0D0;
            }
        """)
        zoom_layout = QHBoxLayout(zoom_bar)
        zoom_layout.setContentsMargins(8, 2, 8, 2)
        zoom_layout.setSpacing(6)

        # Zoom out button
        btn_out = QPushButton("−")
        btn_out.setFixedSize(24, 24)
        btn_out.setToolTip("Alejar (Ctrl+-)")
        btn_out.clicked.connect(self._zoom_out)
        btn_out.setStyleSheet(_ZOOM_BTN_STYLE)
        zoom_layout.addWidget(btn_out)

        # Zoom slider
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(_MIN_ZOOM, _MAX_ZOOM)
        self._zoom_slider.setValue(_DEFAULT_ZOOM)
        self._zoom_slider.setTickInterval(25)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider)
        self._zoom_slider.setStyleSheet(_SLIDER_STYLE)
        zoom_layout.addWidget(self._zoom_slider)

        # Zoom in button
        btn_in = QPushButton("+")
        btn_in.setFixedSize(24, 24)
        btn_in.setToolTip("Acercar (Ctrl++)")
        btn_in.clicked.connect(self._zoom_in)
        btn_in.setStyleSheet(_ZOOM_BTN_STYLE)
        zoom_layout.addWidget(btn_in)

        # Zoom label
        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(40)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet("font-size: 9pt; color: #555; font-weight: bold;")
        zoom_layout.addWidget(self._zoom_label)

        zoom_layout.addStretch()

        # ── Status info (right side of zoom bar) ────────────────────────────
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 8pt; color: #777;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        zoom_layout.addWidget(self._status_label)

        layout.addWidget(zoom_bar)

        # Enable Ctrl+Scroll zoom on the canvas
        self._canvas.viewport().installEventFilter(self)

    # ── Public API ──────────────────────────────────────────────────────────

    def show_document(self, qt_doc: QTextDocument) -> None:
        """Replace the current content with the given QTextDocument."""
        self._doc = qt_doc
        self._canvas.setDocument(qt_doc)
        self._apply_zoom()
        self._update_status()

    def set_document_stats(
        self,
        word_count: int = 0,
        section_count: int = 0,
        ref_count: int = 0,
        font_name: str = "Times New Roman",
    ) -> None:
        """Update the status bar with document statistics."""
        self._word_count = word_count
        self._section_count = section_count
        self._ref_count = ref_count
        self._font_name = font_name
        self._update_status()

    # ── Zoom controls ───────────────────────────────────────────────────────

    def _zoom_in(self) -> None:
        self._set_zoom(min(self._zoom + _ZOOM_STEP, _MAX_ZOOM))

    def _zoom_out(self) -> None:
        self._set_zoom(max(self._zoom - _ZOOM_STEP, _MIN_ZOOM))

    def _on_zoom_slider(self, value: int) -> None:
        self._set_zoom(value)

    def _set_zoom(self, value: int) -> None:
        self._zoom = value
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(value)
        self._zoom_slider.blockSignals(False)
        self._zoom_label.setText(f"{value}%")
        self._apply_zoom()
        self.zoom_changed.emit(value)

    def _apply_zoom(self) -> None:
        """Apply zoom by scaling the font size of the QTextDocument."""
        if self._doc:
            factor = self._zoom / 100.0
            # Scale the default font of the document
            font = self._doc.defaultFont()
            font.setPointSizeF(12 * factor)
            self._doc.setDefaultFont(font)

    # ── Ctrl+Scroll zoom ───────────────────────────────────────────────────

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        """Intercept Ctrl+Scroll on canvas viewport for zoom."""
        if obj == self._canvas.viewport() and isinstance(event, QWheelEvent):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom_in()
                elif delta < 0:
                    self._zoom_out()
                return True
        return super().eventFilter(obj, event)

    # ── Status bar ──────────────────────────────────────────────────────────

    def _update_status(self) -> None:
        """Update the status label with document info."""
        parts = []

        if self._doc:
            # Estimate pages from block count (rough: ~25 lines per page)
            block_count = self._doc.blockCount()
            est_pages = max(1, (block_count + 24) // 25)
            parts.append(f"~{est_pages} pág.")

        if self._word_count > 0:
            parts.append(f"{self._word_count:,} palabras")

        if self._section_count > 0:
            parts.append(f"{self._section_count} secciones")

        if self._ref_count > 0:
            parts.append(f"{self._ref_count} refs")

        parts.append(f"🔤 {self._font_name} 12pt")

        self._status_label.setText("  •  ".join(parts))


# ---------------------------------------------------------------------------
# Stylesheets
# ---------------------------------------------------------------------------

_ZOOM_BTN_STYLE = """
QPushButton {
    background: #DDDDDD;
    color: #333;
    border: 1px solid #BBBBBB;
    border-radius: 3px;
    font-size: 14pt;
    font-weight: bold;
    padding: 0;
}
QPushButton:hover {
    background: #CCCCCC;
}
QPushButton:pressed {
    background: #BBBBBB;
}
"""

_SLIDER_STYLE = """
QSlider::groove:horizontal {
    height: 4px;
    background: #CCCCCC;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background: #4A90D9;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #357ABD;
}
"""
