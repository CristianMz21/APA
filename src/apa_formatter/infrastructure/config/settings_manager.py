"""Settings manager — loads/saves UserSettings to OS-appropriate config dir.

Implements ``SettingsPort`` and persists user preferences as JSON to
``~/.config/apa_formatter/user_settings.json`` (Linux) or the equivalent
platform directory via ``platformdirs``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import platformdirs

from apa_formatter.domain.models.settings import UserSettings
from apa_formatter.domain.ports.settings_port import SettingsPort

_APP_NAME = "apa_formatter"
_SETTINGS_FILENAME = "user_settings.json"


class SettingsManager(SettingsPort):
    """Concrete implementation of :class:`SettingsPort`.

    Parameters
    ----------
    config_dir : Path | None
        Override the default config directory (useful for testing).
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or Path(
            platformdirs.user_config_dir(_APP_NAME, ensure_exists=True)
        )
        self._settings_path = self._config_dir / _SETTINGS_FILENAME

    # -- Public API ----------------------------------------------------------

    def load(self) -> UserSettings:
        """Load user settings from disk, falling back to defaults."""
        if not self._settings_path.exists():
            return UserSettings()

        try:
            raw = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return UserSettings.model_validate(raw)
        except Exception:
            # Corrupted file → return safe defaults
            return UserSettings()

    def save(self, settings: UserSettings) -> None:
        """Persist settings atomically (write to temp, then rename)."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        data = settings.model_dump(mode="json")
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self._config_dir,
            suffix=".tmp",
        )
        try:
            with open(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            Path(tmp_path).replace(self._settings_path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def reset_to_defaults(self) -> UserSettings:
        """Delete the persisted file and return factory defaults."""
        self._settings_path.unlink(missing_ok=True)
        return UserSettings()

    @property
    def settings_path(self) -> Path:
        """Absolute path to the user settings JSON file."""
        return self._settings_path
