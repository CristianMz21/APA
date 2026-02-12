"""Reusable async operation overlay with progress indicator.

Provides ``AsyncWorker`` (QThread wrapper) and ``AsyncOverlay`` (semi-transparent
spinner widget) to run blocking tasks without freezing the GUI.

Usage::

    worker = AsyncWorker(my_blocking_fn, arg1, arg2)
    overlay = AsyncOverlay(parent_widget, "Processing…")
    overlay.run(worker)
    worker.finished.connect(lambda result: handle(result))
    worker.error.connect(lambda exc: show_error(exc))
"""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from PySide6.QtCore import QThread


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------


class AsyncWorker(QThread):
    """Run a callable in a background thread with result/error signals."""

    finished = Signal(object)  # emits the return value
    error = Signal(object)  # emits the exception
    progress = Signal(str)  # optional progress messages

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:  # noqa: D102
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(exc)


# ---------------------------------------------------------------------------
# Spinner overlay
# ---------------------------------------------------------------------------


class AsyncOverlay(QWidget):
    """Semi-transparent overlay with animated spinner and cancel button."""

    cancelled = Signal()

    def __init__(
        self,
        parent: QWidget,
        message: str = "Procesando…",
        *,
        cancellable: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAutoFillBackground(False)

        self._angle = 0
        self._message = message
        self._worker: AsyncWorker | None = None

        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Message label
        self._label = QLabel(message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._label)

        # Cancel button
        self._cancel_btn = QPushButton("✕ Cancelar")
        self._cancel_btn.setFixedWidth(120)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.2); color: white; "
            "border: 1px solid rgba(255,255,255,0.4); border-radius: 4px; "
            "padding: 6px 12px; font-size: 9pt; }"
            "QPushButton:hover { background: rgba(255,255,255,0.35); }"
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setVisible(cancellable)
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Spinner timer
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(30)
        self._spin_timer.timeout.connect(self._tick)

        self.hide()

    # -- Public API ----------------------------------------------------------

    def set_message(self, msg: str) -> None:
        """Update the displayed message."""
        self._message = msg
        self._label.setText(msg)

    def run(self, worker: AsyncWorker) -> None:
        """Start the worker and show the overlay."""
        self._worker = worker
        worker.finished.connect(self._on_done)
        worker.error.connect(self._on_done)
        worker.progress.connect(self.set_message)

        # Size to parent
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._spin_timer.start()
        worker.start()

    def dismiss(self) -> None:
        """Hide the overlay and stop the spinner."""
        self._spin_timer.stop()
        self.hide()

    # -- Internal ------------------------------------------------------------

    def _on_done(self, _result: object = None) -> None:
        self.dismiss()

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
        self.dismiss()
        self.cancelled.emit()

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    # -- Paint ---------------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802, D102
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 140))

        # Spinner arc
        center = self.rect().center()
        r = 24
        pen = QPen(QColor(255, 255, 255, 200), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        from PySide6.QtCore import QRectF

        arc_rect = QRectF(center.x() - r, center.y() - r - 40, r * 2, r * 2)
        painter.drawArc(arc_rect, int(self._angle * 16), int(270 * 16))

        painter.end()

    def resizeEvent(self, event) -> None:  # noqa: N802, D102
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())


"""
:param:
:type:
:return:
:rtype:
"""
