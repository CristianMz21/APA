"""Application layer — Config DTO.

Re-exports the APAConfig Pydantic model from the original config/models.py.
During migration, this acts as the canonical entry point for configuration
DTOs. The actual model definition stays in config/models.py until Phase 4
moves it to infrastructure, at which point this module will hold the
authoritative copy.
"""

# Temporary re-export: config models haven't moved yet (Phase 4).
# This will be updated when infrastructure config is migrated.
from apa_formatter.config.models import APAConfig  # noqa: F401

__all__ = ["APAConfig"]
