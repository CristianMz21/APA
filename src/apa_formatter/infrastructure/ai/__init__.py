"""AI infrastructure — Google Gemini integration."""

try:
    from apa_formatter.infrastructure.ai.gemini_client import (
        GeminiAnalysisError,
        GeminiClient,
    )

    __all__ = ["GeminiClient", "GeminiAnalysisError"]
except ImportError:
    # google-genai not installed — AI features unavailable
    __all__: list[str] = []  # type: ignore[no-redef]
