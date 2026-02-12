"""System clipboard — implements ClipboardPort using subprocess."""

from __future__ import annotations

import subprocess
import sys

from apa_formatter.domain.errors import ClipboardError as DomainClipboardError
from apa_formatter.domain.ports.clipboard_port import ClipboardPort


def _detect_backend() -> list[str]:
    """Return the clipboard command appropriate for this OS.

    Returns:
        CLI command tokens (e.g. ``['xclip', '-selection', 'clipboard']``).

    Raises:
        DomainClipboardError: No supported clipboard tool found.
    """
    if sys.platform == "darwin":
        return ["pbcopy"]

    if sys.platform.startswith("linux"):
        for cmd in (
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
        ):
            try:
                subprocess.run(
                    [cmd[0], "--version"],
                    capture_output=True,
                    check=False,
                )
                return cmd
            except FileNotFoundError:
                continue
        raise DomainClipboardError("No clipboard tool found. Install xclip or xsel.")

    if sys.platform == "win32":
        return ["clip"]

    raise DomainClipboardError(f"Unsupported platform: {sys.platform}")


class SystemClipboard(ClipboardPort):
    """Clipboard adapter using OS-level subprocess commands."""

    def copy(self, text: str) -> None:
        """Copy text to system clipboard via subprocess."""
        cmd = _detect_backend()
        try:
            subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            raise DomainClipboardError(f"Clipboard copy failed: {exc}") from exc
