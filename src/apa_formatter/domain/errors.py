"""Domain errors — custom exceptions for APA Formatter.

These exceptions are raised by domain services and caught by application
or presentation layers. They carry no infrastructure dependencies.
"""


class APAFormatterError(Exception):
    """Base exception for all APA Formatter errors."""


class APAValidationError(APAFormatterError):
    """Raised when domain validation fails (e.g., invalid Reference data)."""


class ReferenceNotFoundError(APAFormatterError):
    """Raised when a reference cannot be found by index or identifier."""


class DocumentGenerationError(APAFormatterError):
    """Raised when document rendering fails."""


class ConfigurationError(APAFormatterError):
    """Raised when configuration is invalid or missing."""


class MetadataFetchError(APAFormatterError):
    """Raised when fetching metadata from external sources fails."""


class ClipboardError(APAFormatterError):
    """Raised when clipboard operations fail."""
