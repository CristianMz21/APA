"""User-friendly error messages for Pydantic validation errors.

Belongs to the Application layer — translates Pydantic machine errors
into localised, user-friendly messages.
"""

from __future__ import annotations

from typing import Any

# Maps (field, error_type) → message key
_ERROR_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("doi", "value_error"): {
        "en": "Invalid DOI format. Expected: 10.XXXX/... (e.g., 10.1037/amp0000722)",
        "es": "Formato de DOI inválido. Esperado: 10.XXXX/... (ej., 10.1037/amp0000722)",
    },
    ("year", "int_parsing"): {
        "en": "Year must be a number (e.g., 2023).",
        "es": "El año debe ser un número (ej., 2023).",
    },
    ("ref_type", "enum"): {
        "en": "Invalid reference type. Check ReferenceType enum for valid options.",
        "es": "Tipo de referencia inválido. Consulte ReferenceType para opciones válidas.",
    },
    ("authors", "missing"): {
        "en": "At least one author is required.",
        "es": "Se requiere al menos un autor.",
    },
    ("title", "missing"): {
        "en": "Title is required.",
        "es": "El título es obligatorio.",
    },
    ("url", "url_parsing"): {
        "en": "Invalid URL format. Must start with http:// or https://",
        "es": "Formato de URL inválido. Debe comenzar con http:// o https://",
    },
}


def friendly_error(
    field: str,
    error_type: str,
    lang: str = "en",
    fallback: str | None = None,
) -> str:
    """Return a user-friendly error message.

    Args:
        field: The Pydantic field name that failed validation.
        error_type: The Pydantic error type string (e.g., ``value_error``).
        lang: Language code (``en`` or ``es``).
        fallback: Fallback message if no mapping exists.

    Returns:
        A localised, user-friendly error string.
    """
    key = (field, error_type)
    messages = _ERROR_MAP.get(key)
    if messages:
        return messages.get(lang, messages.get("en", ""))
    return fallback or f"Validation error on field '{field}'."


def format_validation_errors(
    errors: list[dict[str, Any]],
    lang: str = "en",
) -> list[str]:
    """Convert a list of Pydantic error dicts to user-friendly messages.

    Args:
        errors: Output of ``ValidationError.errors()``.
        lang: Language code.

    Returns:
        List of user-friendly error strings.
    """
    result: list[str] = []
    for err in errors:
        field = ".".join(str(loc) for loc in err.get("loc", []))
        error_type = err.get("type", "")
        msg = friendly_error(field, error_type, lang, fallback=err.get("msg"))
        result.append(msg)
    return result
