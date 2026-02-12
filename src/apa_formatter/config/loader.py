"""Configuration loader for APA 7 formatter.

Loads the JSON configuration file and returns a validated APAConfig instance.
Uses module-level caching so the config is only parsed once per process.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from apa_formatter.config.models import APAConfig

# Module-level cache
_config_cache: dict[str, APAConfig] = {}

# Default config path — lives next to this module
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "apa7_default.json"


def load_config(path: Optional[Path] = None) -> APAConfig:
    """Load and validate APA config from a JSON file.

    Parameters
    ----------
    path : Path | None
        Path to a custom JSON config file.
        If ``None``, the built-in ``apa7_default.json`` is used.

    Returns
    -------
    APAConfig
        Validated configuration instance.

    Raises
    ------
    FileNotFoundError
        If the specified path does not exist.
    pydantic.ValidationError
        If the JSON content does not match the expected schema.
    """
    config_path = path or _DEFAULT_CONFIG_PATH
    cache_key = str(config_path.resolve())

    if cache_key in _config_cache:
        return _config_cache[cache_key]

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    config = APAConfig.model_validate(raw)
    _config_cache[cache_key] = config
    return config


def get_config() -> APAConfig:
    """Get the default APA 7 configuration (cached).

    This is the main entry point used by the rest of the application.
    """
    return load_config()


def clear_cache() -> None:
    """Clear the config cache — useful for testing."""
    _config_cache.clear()
