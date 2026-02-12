"""Smart reference fetch widget — auto-detect DOI/ISBN/URL and fetch metadata.

Embeds as a compact bar at the top of ``ReferenceDialog``.  Identifies the
identifier type, fetches metadata via the appropriate backend fetcher using
``AsyncWorker``, and emits the resulting ``Reference`` for the dialog to
auto-populate its fields.

Usage::

    fetch_widget = ReferenceFetchWidget()
    fetch_widget.reference_fetched.connect(dialog._populate)
    layout.insertWidget(0, fetch_widget)
"""

from __future__ import annotations

import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apa_formatter.gui.theme import RADIUS_SM, SPACING_MD, SPACING_SM, Theme
from apa_formatter.gui.widgets.async_overlay import AsyncWorker
from apa_formatter.models.document import Reference


# ---------------------------------------------------------------------------
# Identifier detection
# ---------------------------------------------------------------------------

_DOI_PATTERN = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/)?10\.\d{4,}/\S+",
    re.IGNORECASE,
)
_ISBN_PATTERN = re.compile(
    r"^[\d\- ]{10,17}$",  # ISBN-10 or ISBN-13 (with hyphens/spaces)
)
_URL_PATTERN = re.compile(
    r"^https?://",
    re.IGNORECASE,
)


def _detect_identifier(text: str) -> str | None:
    """Return 'doi', 'isbn', 'url', or None."""
    text = text.strip()
    if not text:
        return None
    if _DOI_PATTERN.match(text):
        return "doi"
    if _ISBN_PATTERN.match(text):
        return "isbn"
    if _URL_PATTERN.match(text):
        return "url"
    return None


# ---------------------------------------------------------------------------
# Fetch functions dispatcher
# ---------------------------------------------------------------------------


def _fetch_reference(identifier_type: str, value: str) -> Reference:
    """Call the appropriate backend fetcher."""
    if identifier_type == "doi":
        from apa_formatter.fetchers.doi_fetcher import fetch_by_doi

        return fetch_by_doi(value)
    elif identifier_type == "isbn":
        from apa_formatter.fetchers.isbn_fetcher import fetch_by_isbn

        return fetch_by_isbn(value)
    elif identifier_type == "url":
        from apa_formatter.fetchers.url_fetcher import fetch_by_url

        return fetch_by_url(value)
    msg = f"Unknown identifier type: {identifier_type}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

_TYPE_LABELS = {
    "doi": ("🔗 DOI detectado", "#4A6CF7"),
    "isbn": ("📖 ISBN detectado", "#27AE60"),
    "url": ("🌐 URL detectada", "#E67E22"),
}


class ReferenceFetchWidget(QFrame):
    """Compact fetch bar: input + detect + fetch button + status.

    Signals:
        reference_fetched(Reference): emitted with the populated Reference.
    """

    reference_fetched = Signal(object)  # Reference

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._worker: AsyncWorker | None = None
        self._detected_type: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("🔍 Buscar por identificador")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("DOI, ISBN o URL — pega aquí para buscar…")
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_fetch)
        input_row.addWidget(self._input, stretch=1)

        self._fetch_btn = QPushButton("🔎 Buscar")
        self._fetch_btn.setEnabled(False)
        self._fetch_btn.clicked.connect(self._on_fetch)
        input_row.addWidget(self._fetch_btn)

        layout.addLayout(input_row)

        # Status row
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._apply_style()

    # -- Public API ----------------------------------------------------------

    def reset(self) -> None:
        """Clear the input and status."""
        self._input.clear()
        self._status.clear()
        self._detected_type = None

    # -- Internal ------------------------------------------------------------

    def _on_text_changed(self, text: str) -> None:
        """Auto-detect identifier type as the user types."""
        self._detected_type = _detect_identifier(text)
        if self._detected_type:
            label, color = _TYPE_LABELS.get(self._detected_type, ("•", "#888"))
            self._status.setText(label)
            self._status.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: bold;")
            self._fetch_btn.setEnabled(True)
        else:
            self._status.clear()
            self._fetch_btn.setEnabled(False)

    def _on_fetch(self) -> None:
        """Start async fetch using detected identifier type."""
        if not self._detected_type:
            return

        value = self._input.text().strip()
        if not value:
            return

        # Disable button during fetch
        self._fetch_btn.setEnabled(False)
        self._fetch_btn.setText("⏳ Buscando…")

        p = Theme.palette()
        self._status.setText("Consultando base de datos…")
        self._status.setStyleSheet(f"color: {p.text_muted}; font-size: 9pt; font-style: italic;")

        self._worker = AsyncWorker(_fetch_reference, self._detected_type, value)
        self._worker.finished.connect(self._on_fetch_done)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_done(self, result: object) -> None:
        """Handle successful fetch."""
        self._fetch_btn.setText("🔎 Buscar")
        self._fetch_btn.setEnabled(True)

        if isinstance(result, Reference):
            p = Theme.palette()
            self._status.setText(
                f"✅ Encontrado: {result.title[:60]}…"
                if len(result.title) > 60
                else f"✅ Encontrado: {result.title}"
            )
            self._status.setStyleSheet(f"color: {p.success}; font-size: 9pt; font-weight: bold;")
            self.reference_fetched.emit(result)

    def _on_fetch_error(self, exc: object) -> None:
        """Handle fetch error."""
        self._fetch_btn.setText("🔎 Buscar")
        self._fetch_btn.setEnabled(True)

        p = Theme.palette()
        self._status.setText(f"❌ Error: {exc}")
        self._status.setStyleSheet(f"color: {p.error}; font-size: 9pt;")

    def _apply_style(self) -> None:
        p = Theme.palette()
        self.setStyleSheet(f"""
            ReferenceFetchWidget {{
                background: {p.accent_subtle};
                border: 1px solid {p.border_light};
                border-radius: {RADIUS_SM};
            }}
        """)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {p.bg_surface};
                border: 1px solid {p.border};
                border-radius: {RADIUS_SM};
                padding: {SPACING_SM} {SPACING_MD};
                font-size: 10pt;
                color: {p.text_primary};
            }}
            QLineEdit:focus {{
                border-color: {p.border_focus};
            }}
        """)
        self._fetch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p.accent};
                color: {p.text_inverse};
                border: none;
                border-radius: {RADIUS_SM};
                padding: {SPACING_SM} {SPACING_MD};
                font-size: 10pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {p.accent_hover}; }}
            QPushButton:disabled {{
                background: {p.border};
                color: {p.text_muted};
            }}
        """)
