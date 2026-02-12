"""APA Auto-Correction Pipeline.

Provides intelligent, offline auto-formatting of raw text into
APA 7th Edition–compliant documents using a chain of regex-based fixers.
"""

from apa_formatter.automation.pipeline import APAAutoFormatter

__all__ = ["APAAutoFormatter"]
