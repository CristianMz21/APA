"""Robust wrapper for the Google Generative AI (Gemini) API.

Provides a ``GeminiClient`` that:

* Reads ``GEMINI_API_KEY`` from environment (via ``python-dotenv``).
* Implements exponential-backoff retries for rate-limit / transient errors.
* Enforces structured JSON output through ``response_mime_type``.
* Wraps all errors in a single ``GeminiAnalysisError`` exception.

Usage::

    from apa_formatter.infrastructure.ai.gemini_client import GeminiClient

    client = GeminiClient()          # reads .env automatically
    result = client.analyze_text(
        text="Portada de un documento…",
        schema=AiSemanticResult,     # any Pydantic BaseModel
        system_prompt="Eres un editor APA 7…",
    )
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — only fail when actually instantiated
# ---------------------------------------------------------------------------

_HAS_GENAI = False
try:
    from google import genai  # type: ignore[import-untyped]

    _HAS_GENAI = True
except ImportError:
    pass

try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]
except ImportError:

    def load_dotenv(*_args: Any, **_kwargs: Any) -> None:  # noqa: D103
        pass


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class GeminiAnalysisError(Exception):
    """Raised when a Gemini API call fails after all retries."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "gemini-2.5-flash"
_MAX_RETRIES = 3
_INITIAL_DELAY_S = 1.0
_MAX_DELAY_S = 30.0
_BACKOFF_BASE = 2.0
_JITTER_FACTOR = 0.5
_RETRYABLE_STATUS_CODES = {429, 500, 503}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GeminiClient:
    """Thread-safe, retry-aware wrapper around the Google Gen AI SDK.

    Parameters
    ----------
    api_key:
        Explicit API key.  Falls back to ``GEMINI_API_KEY`` env var.
    model:
        Model identifier.  Falls back to ``GEMINI_MODEL`` env var,
        then ``gemini-2.5-flash``.
    max_retries:
        Maximum retry attempts for transient errors.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        if not _HAS_GENAI:
            raise ImportError(
                "google-genai is not installed. Install it with: pip install 'apa-formatter[ai]'"
            )

        load_dotenv()

        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in your environment or "
                "in a .env file. Get a key at https://aistudio.google.com/apikey"
            )

        self._model = model or os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL)
        self._max_retries = max_retries
        self._client = genai.Client(api_key=self._api_key)

        logger.info("GeminiClient initialized with model=%s", self._model)

    # -- Public API ----------------------------------------------------------

    def analyze_text(
        self,
        text: str,
        schema: Type[BaseModel],
        system_prompt: str,
    ) -> dict[str, Any]:
        """Send *text* to Gemini and return structured JSON matching *schema*.

        Parameters
        ----------
        text:
            Raw text fragment to analyse.
        schema:
            Pydantic model class whose JSON schema constrains the output.
        system_prompt:
            System-level instruction for the model.

        Returns
        -------
        dict
            Parsed JSON matching the schema.

        Raises
        ------
        GeminiAnalysisError
            If all retries are exhausted or an unrecoverable error occurs.
        """
        json_schema = schema.model_json_schema()
        return self._call_with_retry(text, json_schema, system_prompt)

    @property
    def model_name(self) -> str:
        """Return the configured model identifier."""
        return self._model

    # -- Internal retry logic ------------------------------------------------

    def _call_with_retry(
        self,
        text: str,
        json_schema: dict[str, Any],
        system_prompt: str,
    ) -> dict[str, Any]:
        """Execute the API call with exponential backoff."""
        last_error: Exception | None = None
        delay = _INITIAL_DELAY_S

        for attempt in range(1, self._max_retries + 1):
            try:
                return self._make_request(text, json_schema, system_prompt)
            except Exception as exc:
                last_error = exc

                # Check if retryable
                if not self._is_retryable(exc):
                    logger.error(
                        "Non-retryable Gemini error (attempt %d/%d): %s",
                        attempt,
                        self._max_retries,
                        exc,
                    )
                    raise GeminiAnalysisError(f"Gemini API error (non-retryable): {exc}") from exc

                if attempt < self._max_retries:
                    jitter = random.uniform(0, delay * _JITTER_FACTOR)
                    sleep_time = min(delay + jitter, _MAX_DELAY_S)
                    logger.warning(
                        "Retryable Gemini error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt,
                        self._max_retries,
                        sleep_time,
                        exc,
                    )
                    time.sleep(sleep_time)
                    delay *= _BACKOFF_BASE

        raise GeminiAnalysisError(
            f"Gemini API failed after {self._max_retries} retries: {last_error}"
        ) from last_error

    def _make_request(
        self,
        text: str,
        json_schema: dict[str, Any],
        system_prompt: str,
    ) -> dict[str, Any]:
        """Execute a single API request."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=text,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": json_schema,
                "system_instruction": system_prompt,
            },
        )

        raw_text = response.text
        if not raw_text:
            raise GeminiAnalysisError("Gemini returned empty response")

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise GeminiAnalysisError(f"Gemini returned invalid JSON: {raw_text[:200]}") from exc

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Check whether an exception warrants a retry."""
        exc_str = str(exc).lower()
        # Rate limit or transient server errors
        if "429" in exc_str or "rate limit" in exc_str:
            return True
        if "500" in exc_str or "503" in exc_str:
            return True
        if "resource exhausted" in exc_str:
            return True
        if "service unavailable" in exc_str:
            return True
        return False
