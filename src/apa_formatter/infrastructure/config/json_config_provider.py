"""JSON config provider — implements ConfigProviderPort.

Wraps the existing config/loader.py logic.
"""

from __future__ import annotations

from typing import Any

from apa_formatter.domain.ports.config_provider import ConfigProviderPort


class JsonConfigProvider(ConfigProviderPort):
    """Load APA configuration from JSON files.

    Delegates to the existing config loader during migration.
    """

    def __init__(self, config_path: str | None = None) -> None:
        self._config_path = config_path
        self._config: Any = None

    def get_config(self) -> Any:
        """Return the current APA configuration, loading lazily."""
        if self._config is None:
            from apa_formatter.config.loader import get_config

            if self._config_path:
                from apa_formatter.config.loader import load_config

                self._config = load_config(self._config_path)
            else:
                self._config = get_config()
        return self._config
