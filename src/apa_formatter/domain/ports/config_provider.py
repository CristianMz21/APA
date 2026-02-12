"""Port: Configuration provider — supply APA formatting configuration."""

from abc import ABC, abstractmethod
from typing import Any


class ConfigProviderPort(ABC):
    """Contract for providing configuration to the application.

    The concrete return type is intentionally ``Any`` at the domain level.
    The Application layer's DTO (``APAConfig``) provides the typed contract.
    This keeps the domain free of Pydantic config model dependencies.
    """

    @abstractmethod
    def get_config(self) -> Any:
        """Return the current APA configuration object."""
        ...
