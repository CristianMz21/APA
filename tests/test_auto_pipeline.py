"""Tests for the APA Auto-Correction Pipeline.

Covers every fixer individually plus the full pipeline integration.
"""

from __future__ import annotations

import re

from apa_formatter.automation.base import BaseFixer, FixCategory, FixEntry, FixResult
from apa_formatter.automation.fixers.character_fixer import CharacterFixer
from apa_formatter.automation.fixers.citation_fixer import CitationFixer
from apa_formatter.automation.fixers.heading_detector import HeadingDetector
from apa_formatter.automation.fixers.paragraph_fixer import ParagraphFixer
from apa_formatter.automation.fixers.reference_list_fixer import ReferenceListFixer
from apa_formatter.automation.fixers.whitespace_fixer import WhitespaceFixer
from apa_formatter.automation.pipeline import APAAutoFormatter


# ═══════════════════════════════════════════════════════════════════════════
# Base / Data types
# ═══════════════════════════════════════════════════════════════════════════


class TestFixResult:
    def test_total_fixes(self) -> None:
        r = FixResult(
            text="x",
            entries=[
                FixEntry(FixCategory.WHITESPACE, "a", count=3),
                FixEntry(FixCategory.CITATION, "b", count=2),
            ],
        )
        assert r.total_fixes == 5

    def test_summary_no_fixes(self) -> None:
        r = FixResult(text="ok")
        assert "No se realizaron" in r.summary()

    def test_summary_with_fixes(self) -> None:
        r = FixResult(
            text="ok",
            entries=[FixEntry(FixCategory.WHITESPACE, "spaces", count=3)],
        )
        s = r.summary()
        assert "×3" in s
        assert "Total" in s


# ═══════════════════════════════════════════════════════════════════════════
# WhitespaceFixer
# ═══════════════════════════════════════════════════════════════════════════


class TestWhitespaceFixer:
    def setup_method(self) -> None:
        self.fixer = WhitespaceFixer()

    def test_double_space_after_period(self) -> None:
        r = self.fixer.fix("Hello world.  This is text.")
        assert r.text == "Hello world. This is text."
        assert r.total_fixes > 0

    def test_multiple_spaces_between_words(self) -> None:
        r = self.fixer.fix("One   two    three")
        assert r.text == "One two three"

    def test_trailing_whitespace(self) -> None:
        r = self.fixer.fix("Hello   \nWorld   ")
        assert "   " not in r.text

    def test_excessive_blank_lines(self) -> None:
        r = self.fixer.fix("A\n\n\n\n\nB")
        assert r.text == "A\n\nB"

    def test_no_changes_needed(self) -> None:
        r = self.fixer.fix("Clean text. All good.")
        assert r.total_fixes == 0

    def test_mixed_issues(self) -> None:
        r = self.fixer.fix("A.  B   C   \n\n\n\nD")
        assert "  " not in r.text
        assert r.text.count("\n") <= 2


# ═══════════════════════════════════════════════════════════════════════════
# CharacterFixer
# ═══════════════════════════════════════════════════════════════════════════


class TestCharacterFixer:
    def setup_method(self) -> None:
        self.fixer = CharacterFixer()

    def test_smart_double_quotes(self) -> None:
        r = self.fixer.fix('She said "hello" to him.')
        assert "\u201c" in r.text  # "
        assert "\u201d" in r.text  # "
        assert '"' not in r.text

    def test_spaced_hyphen_to_em_dash(self) -> None:
        r = self.fixer.fix("El resultado - según los datos - fue positivo.")
        assert "—" in r.text
        assert " - " not in r.text

    def test_double_hyphen_to_em_dash(self) -> None:
        r = self.fixer.fix("El resultado--fue positivo.")
        assert "—" in r.text
        assert "--" not in r.text

    def test_three_dots_to_ellipsis(self) -> None:
        r = self.fixer.fix("Esperando...")
        assert "…" in r.text
        assert "..." not in r.text

    def test_no_changes_on_clean_text(self) -> None:
        r = self.fixer.fix("Clean text without issues.")
        assert r.total_fixes == 0


# ═══════════════════════════════════════════════════════════════════════════
# HeadingDetector
# ═══════════════════════════════════════════════════════════════════════════


class TestHeadingDetector:
    def setup_method(self) -> None:
        self.fixer = HeadingDetector()

    def test_known_heading_l1(self) -> None:
        r = self.fixer.fix("Introducción\n\nContenido aquí.")
        assert "# Introducción" in r.text
        assert r.total_fixes >= 1

    def test_uppercase_heading_l1(self) -> None:
        r = self.fixer.fix("\nMETODOLOGÍA\n\nTexto del método.")
        assert "# " in r.text

    def test_bold_heading_l2(self) -> None:
        r = self.fixer.fix("\n**Participantes**\n\nTexto.")
        assert "## " in r.text

    def test_italic_heading_l3(self) -> None:
        r = self.fixer.fix("\n*Instrumentos*\n\nTexto.")
        assert "### " in r.text

    def test_title_case_applied(self) -> None:
        r = self.fixer.fix("RESULTS AND DISCUSSION\n\nText.")
        assert "Results" in r.text
        # Minor word "and" should be lowercase
        assert "and" in r.text.lower()

    def test_existing_markdown_headings_preserved(self) -> None:
        r = self.fixer.fix("# My Heading\n\nContent.")
        assert "# My Heading" in r.text

    def test_normal_paragraphs_not_affected(self) -> None:
        text = "This is a regular paragraph with more than enough words to not be a heading.\n\nAnother paragraph."
        r = self.fixer.fix(text)
        assert "#" not in r.text


# ═══════════════════════════════════════════════════════════════════════════
# ParagraphFixer
# ═══════════════════════════════════════════════════════════════════════════


class TestParagraphFixer:
    def setup_method(self) -> None:
        self.fixer = ParagraphFixer()

    def test_indent_normal_paragraph(self) -> None:
        r = self.fixer.fix("# Heading\n\nFirst after heading.\n\nSecond paragraph.")
        lines = r.text.split("\n")
        # First after heading should NOT be indented (APA)
        first_body = [ln for ln in lines if ln.strip() and not ln.startswith("#")][0]
        assert not first_body.startswith("\t")
        # Second paragraph should be indented
        assert any(ln.startswith("\t") for ln in lines)

    def test_no_indent_on_headings(self) -> None:
        r = self.fixer.fix("# Heading\n\nParagraph.")
        assert not any(ln.startswith("\t#") for ln in r.text.split("\n"))

    def test_no_indent_on_list_items(self) -> None:
        r = self.fixer.fix("# Heading\n\n- Item one\n- Item two\n\nParagraph.")
        for line in r.text.split("\n"):
            if line.strip().startswith("-"):
                assert not line.startswith("\t")

    def test_no_indent_on_blockquotes(self) -> None:
        r = self.fixer.fix("# Heading\n\n> Quoted text.\n\nParagraph.")
        for line in r.text.split("\n"):
            if line.strip().startswith(">"):
                assert not line.startswith("\t")


# ═══════════════════════════════════════════════════════════════════════════
# CitationFixer
# ═══════════════════════════════════════════════════════════════════════════


class TestCitationFixer:
    def setup_method(self) -> None:
        self.fixer = CitationFixer()

    def test_narrative_citation(self) -> None:
        r = self.fixer.fix("Según (Smith, 2020) el resultado fue positivo.")
        assert "Según Smith (2020)" in r.text
        assert r.total_fixes >= 1

    def test_narrative_according_to(self) -> None:
        r = self.fixer.fix("According to (García, 2019), the data shows...")
        assert "According to García (2019)" in r.text

    def test_page_locator_p(self) -> None:
        r = self.fixer.fix("(Smith, 2020, p12)")
        assert "p. 12" in r.text

    def test_page_locator_pp(self) -> None:
        r = self.fixer.fix("(Smith, 2020, pp12-20)")
        assert "pp. 12" in r.text

    def test_et_al_on_second_mention(self) -> None:
        text = (
            "First: (Smith, Jones, & Lee, 2020). "
            "Second: (Smith, Jones, & Lee, 2020). "
            "Third: (Smith, Jones, & Lee, 2020)."
        )
        r = self.fixer.fix(text)
        # Second and third should become et al.
        assert "et al." in r.text
        assert r.total_fixes >= 1

    def test_two_authors_no_et_al(self) -> None:
        text = "First: (Smith & Jones, 2020). Second: (Smith & Jones, 2020)."
        r = self.fixer.fix(text)
        assert "et al." not in r.text

    def test_no_changes_on_correct_citations(self) -> None:
        r = self.fixer.fix("Smith (2020) found that results (p. 12) were good.")
        # Should not break already-correct citations
        assert "Smith (2020)" in r.text


# ═══════════════════════════════════════════════════════════════════════════
# ReferenceListFixer
# ═══════════════════════════════════════════════════════════════════════════


class TestReferenceListFixer:
    def setup_method(self) -> None:
        self.fixer = ReferenceListFixer()

    def test_alphabetical_sorting(self) -> None:
        text = (
            "# Referencias\n\n"
            "Zapata, A. (2020). Title. Publisher.\n\n"
            "Adams, B. (2019). Title. Publisher.\n\n"
            "Miller, C. (2021). Title. Publisher."
        )
        r = self.fixer.fix(text)
        lines = [ln.strip() for ln in r.text.split("\n") if ln.strip() and not ln.startswith("#")]
        # Adams should come first
        assert lines[0].startswith("Adams")

    def test_retrieved_from_removed(self) -> None:
        text = "# Referencias\n\nSmith, J. (2020). Title. Retrieved from https://example.com"
        r = self.fixer.fix(text)
        assert "Retrieved from" not in r.text
        assert "https://example.com" in r.text

    def test_recuperado_de_removed(self) -> None:
        text = "# Referencias\n\nGarcía, A. (2020). Título. Recuperado de https://example.com"
        r = self.fixer.fix(text)
        assert "Recuperado de" not in r.text
        assert "https://example.com" in r.text

    def test_angle_brackets_removed(self) -> None:
        text = "# Referencias\n\nSmith, J. (2020). Title. <https://example.com>"
        r = self.fixer.fix(text)
        assert "<https" not in r.text
        assert "https://example.com" in r.text

    def test_no_ref_section_no_changes(self) -> None:
        text = "This is just normal text without references."
        r = self.fixer.fix(text)
        assert r.text == text
        assert r.total_fixes == 0

    def test_hanging_indent_applied(self) -> None:
        text = (
            "# Referencias\n\n"
            "Smith, J. (2020). A very long reference title that should be enough to trigger wrapping when we reach the soft limit. Publisher."
        )
        r = self.fixer.fix(text)
        # Should have tab-indented continuation lines
        assert "\t" in r.text


# ═══════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════


class TestAPAAutoFormatter:
    def test_default_pipeline_has_six_fixers(self) -> None:
        fmt = APAAutoFormatter()
        assert len(fmt.fixer_names) == 6

    def test_fixer_names_order(self) -> None:
        fmt = APAAutoFormatter()
        names = fmt.fixer_names
        assert names[0] == "Whitespace Fixer"
        assert names[1] == "Character Fixer"
        assert names[2] == "Heading Detector"
        assert names[3] == "Paragraph Fixer"
        assert names[4] == "Citation Fixer"
        assert names[5] == "Reference List Fixer"

    def test_add_custom_fixer(self) -> None:
        class DummyFixer(BaseFixer):
            @property
            def name(self) -> str:
                return "Dummy"

            @property
            def category(self) -> FixCategory:
                return FixCategory.WHITESPACE

            def fix(self, text: str) -> FixResult:
                return FixResult(text=text)

        fmt = APAAutoFormatter()
        fmt.add_fixer(DummyFixer())
        assert "Dummy" in fmt.fixer_names
        assert len(fmt.fixer_names) == 7

    def test_add_fixer_at_position(self) -> None:
        class DummyFixer(BaseFixer):
            @property
            def name(self) -> str:
                return "First"

            @property
            def category(self) -> FixCategory:
                return FixCategory.WHITESPACE

            def fix(self, text: str) -> FixResult:
                return FixResult(text=text)

        fmt = APAAutoFormatter()
        fmt.add_fixer(DummyFixer(), position=0)
        assert fmt.fixer_names[0] == "First"

    def test_remove_fixer(self) -> None:
        fmt = APAAutoFormatter()
        removed = fmt.remove_fixer("Heading Detector")
        assert removed
        assert "Heading Detector" not in fmt.fixer_names

    def test_remove_nonexistent_fixer(self) -> None:
        fmt = APAAutoFormatter()
        assert not fmt.remove_fixer("Nonexistent")

    def test_full_pipeline_integration(self) -> None:
        dirty = (
            'Según (Smith, 2020), el resultado  fue  "positivo".\n'
            "La investigación - como se  mencionó - fue importante.\n\n\n\n"
            "RESULTADOS\n\n"
            "El análisis mostró que (Smith, 2020, p12) apoya la hipótesis.\n\n"
            "# Referencias\n\n"
            "Zapata, A. (2020). Título. Retrieved from https://example.com\n\n"
            "Adams, B. (2019). Título. Publisher."
        )
        fmt = APAAutoFormatter()
        r = fmt.run(dirty)

        # Whitespace: no double spaces (strip tabs first — they're intentional indentation)
        text_no_tabs = re.sub(r"^\t", "", r.text, flags=re.MULTILINE)
        assert "  " not in text_no_tabs

        # Characters: smart quotes
        assert '"' not in r.text

        # Characters: em dash
        assert " - " not in r.text

        # Citation: narrative fix
        assert "Según Smith (2020)" in r.text

        # Citation: page locator
        assert "p. 12" in r.text

        # Heading: RESULTADOS detected
        assert "# " in r.text

        # References: sorted (Adams < Zapata)
        lines = [
            ln.strip()
            for ln in r.text.split("\n")
            if ln.strip() and ("Adams" in ln or "Zapata" in ln)
        ]
        if len(lines) >= 2:
            assert r.text.index("Adams") < r.text.index("Zapata")

        # References: no "Retrieved from"
        assert "Retrieved from" not in r.text

        # Change log
        assert r.total_fixes > 0
        summary = r.summary()
        assert "Total" in summary

    def test_empty_text(self) -> None:
        fmt = APAAutoFormatter()
        r = fmt.run("")
        assert r.text == ""

    def test_already_clean_text(self) -> None:
        clean = "# Introducción\n\nTexto limpio sin errores."
        fmt = APAAutoFormatter()
        r = fmt.run(clean)
        assert r.text  # Should still produce output
