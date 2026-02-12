"""AI-powered document corrector using Gemini."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from apa_formatter.domain.models.document import APADocument
from apa_formatter.infrastructure.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class TitleCorrection(BaseModel):
    """Schema for title correction."""

    original: str
    corrected: str = Field(..., description="Title Case formatted version of the title")
    reason: str = Field(..., description="Why the change was made")


class AbstractCorrection(BaseModel):
    """Schema for abstract analysis."""

    is_valid_length: bool = Field(..., description="True if 150-250 words")
    keywords_found: list[str] = Field(default_factory=list)
    suggestion: str | None = Field(None, description="Rewritten abstract if needed")


class AiCorrector:
    """Service to enhance APADocument using AI."""

    def __init__(self, client: GeminiClient) -> None:
        self._client = client

    def correct_document(self, doc: APADocument) -> dict[str, Any]:
        """Analyze and apply corrections to the document.

        Returns a report of changes made.
        """
        report = {
            "title_changed": False,
            "abstract_checked": False,
            "changes": [],
        }

        # 1. Correct Title
        if doc.title_page and doc.title_page.title:
            try:
                self._correct_title(doc, report)
            except Exception as exc:
                logger.warning("Failed to correct title: %s", exc)

        # 2. Check Abstract
        if doc.abstract:
            try:
                self._check_abstract(doc, report)
            except Exception as exc:
                logger.warning("Failed to check abstract: %s", exc)

        return report

    def _correct_title(self, doc: APADocument, report: dict[str, Any]) -> None:
        """Ensure title is in Title Case."""
        current_title = doc.title_page.title
        sys_prompt = (
            "You are an APA 7 style editor. Convert the given title to Title Case "
            "(capitalizing major words, ignoring minor words unless first/last). "
            "Return JSON."
        )

        result = self._client.analyze_text(
            text=current_title,
            schema=TitleCorrection,
            system_prompt=sys_prompt,
        )

        correction = TitleCorrection(**result)
        if correction.corrected != current_title:
            doc.title_page.title = correction.corrected
            report["title_changed"] = True
            report["changes"].append(
                f"Title updated: '{current_title}' -> '{correction.corrected}'"
            )

    def _check_abstract(self, doc: APADocument, report: dict[str, Any]) -> None:
        """Analyze abstract for length and keywords."""
        text = doc.abstract
        sys_prompt = (
            "You are an APA 7 style editor. Check if the abstract is between 150-250 words. "
            "Extract keywords if present. Return JSON."
        )

        result = self._client.analyze_text(
            text=text,
            schema=AbstractCorrection,
            system_prompt=sys_prompt,
        )

        correction = AbstractCorrection(**result)
        report["abstract_checked"] = True

        if not correction.is_valid_length:
            report["changes"].append("Abstract length warning: APA recommends 150-250 words.")

        # If keywords missing in doc but found in text, layout might be wrong,
        # but here we just report.
        if correction.keywords_found and not doc.keywords:
            doc.keywords = correction.keywords_found
            report["changes"].append(f"Extracted keywords: {', '.join(correction.keywords_found)}")
