"""Port (ABC) for user settings persistence.

Domain layer interface — infrastructure provides the concrete implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from apa_formatter.domain.models.settings import UserSettings


class SettingsPort(ABC):
    """Abstract interface for loading / saving user preferences."""

    @abstractmethod
    def load(self) -> UserSettings:
        """Load persisted user settings (or defaults if none exist)."""

    @abstractmethod
    def save(self, settings: UserSettings) -> None:
        """Persist the given user settings."""

    @abstractmethod
    def reset_to_defaults(self) -> UserSettings:
        """Delete persisted settings and return factory defaults."""
