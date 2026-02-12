import unittest
from unittest.mock import MagicMock
from apa_formatter.domain.models.document import APADocument, TitlePage, Section
from apa_formatter.infrastructure.ai.corrector import (
    AiCorrector,
    TitleCorrection,
    AbstractCorrection,
)


class TestAiCorrector(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.corrector = AiCorrector(self.mock_client)
        self.doc = APADocument(
            title_page=TitlePage(
                title="my lowercase title", authors=["John Doe"], affiliation="Uni"
            ),
            sections=[Section(heading="Intro", content="...")],
            abstract="Short abstract.",
        )

    def test_correct_title(self):
        # Setup mock response for title
        self.mock_client.analyze_text.return_value = {
            "original": "my lowercase title",
            "corrected": "My Lowercase Title",
            "reason": "Fixed capitalization",
        }

        # Run correction (only title triggered if abstract is short/empty?
        # Logic says run both if present. Abstract is present.)

        # We need to mock the abstract call too or it will fail if analyze_text is called again with different schema
        # analyze_text is called twice. We can use side_effect.

        def side_effect(text, schema, system_prompt):
            if "title" in system_prompt.lower():
                return {
                    "original": text,
                    "corrected": "My Lowercase Title",
                    "reason": "Fixed capitalization",
                }
            elif "abstract" in system_prompt.lower():
                return {
                    "is_valid_length": False,
                    "keywords_found": ["test", "mock"],
                    "suggestion": None,
                }
            return {}

        self.mock_client.analyze_text.side_effect = side_effect

        report = self.corrector.correct_document(self.doc)

        self.assertTrue(report["title_changed"])
        self.assertEqual(self.doc.title_page.title, "My Lowercase Title")
        self.assertIn("Title updated", report["changes"][0])

        self.assertTrue(report["abstract_checked"])
        self.assertIn("Abstract length warning", report["changes"][1])
        # Keywords should be applied
        self.assertEqual(self.doc.keywords, ["test", "mock"])


if __name__ == "__main__":
    unittest.main()
