"""Clipboard utility — copy formatted APA references to the system clipboard."""

from __future__ import annotations

import subprocess
import sys

from apa_formatter.models.document import Reference


class ClipboardError(RuntimeError):
    """Raised when there is no clipboard backend available."""


def _detect_backend() -> list[str]:
    """Return the clipboard command appropriate for this OS.

    Returns:
        CLI command tokens (e.g. ``['xclip', '-selection', 'clipboard']``).

    Raises:
        ClipboardError: No supported clipboard tool found.
    """
    if sys.platform == "darwin":
        return ["pbcopy"]

    if sys.platform.startswith("linux"):
        # Prefer xclip, fall back to xsel
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
        raise ClipboardError("No clipboard tool found. Install xclip or xsel.")

    if sys.platform == "win32":
        return ["clip"]

    raise ClipboardError(f"Unsupported platform: {sys.platform}")


def copy_to_clipboard(text: str) -> None:
    """Copy *text* to the system clipboard.

    Args:
        text: The string to copy.

    Raises:
        ClipboardError: No clipboard backend or copy failed.
    """
    cmd = _detect_backend()
    try:
        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ClipboardError(f"Clipboard copy failed: {exc}") from exc


def copy_reference(ref: Reference, locale: dict[str, str] | None = None) -> str:
    """Format *ref* as APA and copy it to the clipboard.

    Args:
        ref: The reference to format and copy.
        locale: Optional locale dict for i18n.

    Returns:
        The formatted APA string that was copied.

    Raises:
        ClipboardError: Copy failed.
    """
    formatted = ref.format_apa(locale)
    copy_to_clipboard(formatted)
    return formatted
