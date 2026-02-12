"""Application entry point for the APA 7 Formatter GUI.

Launch with:
    apa-gui          (after pip install -e .)
    python -m apa_formatter.gui.app
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from apa_formatter.gui.main_window import APAMainWindow


def main() -> None:
    """Create the QApplication, show the main window, and enter the event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("APA 7 Formatter")
    app.setOrganizationName("apa-formatter")

    # Apply centralized theme
    from apa_formatter.gui.theme import apply_theme

    apply_theme(app)

    window = APAMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
