"""GUI presentation layer — re-exports from the existing gui/ package.

During the migration, this module delegates to the existing
``apa_formatter.gui`` package.  Once the migration is complete, the
GUI code will live here natively.
"""

from __future__ import annotations


def launch() -> None:
    """Launch the APA Formatter GUI application."""
    from apa_formatter.gui.app import main

    main()
