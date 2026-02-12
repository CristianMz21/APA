"""Unit tests for SmartPdfImporter.

Tests cover:
1. Header / page-number filtering
2. Footer filtering
3. Running head detection
4. Bold detection from fontname
5. Line reconstruction from word positions
6. Paragraph stitching (margin gap + punctuation)
7. Cross-page paragraph merge
8. Heading detection (numbered, ALL-CAPS, bold)
9. Integration: mock pdfplumber → ContentBlock output
10. SemanticImporter routing for .pdf extension
"""

from __future__ import annotations

import pytest

from apa_formatter.importers.strategies.pdf_semantic import (
    SmartPdfImporter,
    _Line,
    _Paragraph,
    _Word,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _w(
    text: str,
    x0: float = 72,
    x1: float = 100,
    top: float = 100,
    bottom: float = 112,
    fontname: str = "TimesNewRomanPSMT",
    size: float = 12.0,
) -> _Word:
    """Shortcut to create a _Word."""
    return _Word(
        text=text,
        x0=x0,
        x1=x1,
        top=top,
        bottom=bottom,
        fontname=fontname,
        size=size,
    )


# ---------------------------------------------------------------------------
# 1. Header / page-number filtering
# ---------------------------------------------------------------------------


class TestHeaderFiltering:
    def test_bare_page_number_in_header_zone_is_filtered(self):
        w = _w("3", top=10)  # top 10 out of 792 → in header zone
        assert SmartPdfImporter._is_header_word(w, 792.0, set()) is True

    def test_body_text_at_top_not_filtered(self):
        w = _w("Introduction", top=10)
        assert SmartPdfImporter._is_header_word(w, 792.0, set()) is False

    def test_number_outside_header_zone_not_filtered(self):
        w = _w("3", top=200)  # well below header zone
        assert SmartPdfImporter._is_header_word(w, 792.0, set()) is False

    def test_running_head_text_is_filtered(self):
        w = _w("catálogo", top=15)
        heads = {"catálogo"}
        assert SmartPdfImporter._is_header_word(w, 792.0, heads) is True

    def test_decorated_page_number_filtered(self):
        w = _w("—3—", top=10)
        assert SmartPdfImporter._is_header_word(w, 792.0, set()) is True

    def test_dash_page_number_filtered(self):
        w = _w("-12-", top=5)
        assert SmartPdfImporter._is_header_word(w, 792.0, set()) is True


# ---------------------------------------------------------------------------
# 2. Footer filtering
# ---------------------------------------------------------------------------


class TestFooterFiltering:
    def test_page_number_in_footer_zone_is_filtered(self):
        w = _w("5", top=760)  # near bottom of 792pt page
        assert SmartPdfImporter._is_footer_word(w, 792.0) is True

    def test_body_text_in_footer_zone_not_filtered(self):
        w = _w("conclusion", top=760)
        assert SmartPdfImporter._is_footer_word(w, 792.0) is False

    def test_page_number_not_near_bottom_not_filtered(self):
        w = _w("5", top=400)
        assert SmartPdfImporter._is_footer_word(w, 792.0) is False


# ---------------------------------------------------------------------------
# 3. Running head detection
# ---------------------------------------------------------------------------


class TestRunningHeadDetection:
    def test_repeated_text_detected(self):
        texts = ["catálogo", "catálogo", "catálogo", "catálogo", "catálogo"]
        heads = SmartPdfImporter._detect_running_heads(texts, 6)
        assert "catálogo" in heads

    def test_single_occurrence_not_detected(self):
        texts = ["catálogo", "intro", "método", "resultado"]
        heads = SmartPdfImporter._detect_running_heads(texts, 6)
        assert "catálogo" not in heads

    def test_page_numbers_excluded_from_running_heads(self):
        texts = ["3", "4", "5", "6", "7"]
        heads = SmartPdfImporter._detect_running_heads(texts, 6)
        assert "3" not in heads

    def test_single_page_returns_empty(self):
        texts = ["catálogo"]
        heads = SmartPdfImporter._detect_running_heads(texts, 1)
        assert heads == set()


# ---------------------------------------------------------------------------
# 4. Bold detection
# ---------------------------------------------------------------------------


class TestBoldDetection:
    def test_bold_fontname(self):
        w = _w("hello", fontname="TimesNewRomanPS-BoldMT")
        assert w.is_bold is True

    def test_non_bold_fontname(self):
        w = _w("hello", fontname="TimesNewRomanPSMT")
        assert w.is_bold is False

    def test_bold_in_lowercase_fontname(self):
        w = _w("hello", fontname="arial-bold")
        assert w.is_bold is True

    def test_bold_italic_fontname(self):
        w = _w("hello", fontname="TimesNewRoman-BoldItalicMT")
        assert w.is_bold is True


# ---------------------------------------------------------------------------
# 5. Line reconstruction
# ---------------------------------------------------------------------------


class TestLineReconstruction:
    def test_words_same_y_form_one_line(self):
        words = [
            _w("Hello", x0=72, x1=100, top=100),
            _w("World", x0=110, x1=140, top=101),  # within tolerance
        ]
        lines = SmartPdfImporter._reconstruct_lines(words)
        assert len(lines) == 1
        assert lines[0].text == "Hello World"

    def test_words_different_y_form_two_lines(self):
        words = [
            _w("Line", x0=72, x1=100, top=100),
            _w("one", x0=110, x1=130, top=100),
            _w("Line", x0=72, x1=100, top=120),
            _w("two", x0=110, x1=130, top=120),
        ]
        lines = SmartPdfImporter._reconstruct_lines(words)
        assert len(lines) == 2
        assert lines[0].text == "Line one"
        assert lines[1].text == "Line two"

    def test_empty_words_returns_empty(self):
        lines = SmartPdfImporter._reconstruct_lines([])
        assert lines == []

    def test_words_sorted_left_to_right(self):
        words = [
            _w("World", x0=110, x1=140, top=100),
            _w("Hello", x0=72, x1=100, top=100),
        ]
        lines = SmartPdfImporter._reconstruct_lines(words)
        assert lines[0].text == "Hello World"


# ---------------------------------------------------------------------------
# 6. Paragraph stitching
# ---------------------------------------------------------------------------


class TestParagraphStitching:
    def _make_line(
        self,
        text: str,
        right_edge: float = 500,
        top: float = 100,
        bold: bool = False,
        size: float = 12.0,
    ) -> _Line:
        words = []
        x = 72.0
        for word_text in text.split():
            w = _w(
                word_text,
                x0=x,
                x1=x + 30,
                top=top,
                bottom=top + 12,
                size=size,
                fontname="Bold" if bold else "Regular",
            )
            words.append(w)
            x += 35
        # Adjust last word's x1 to match desired right edge
        if words:
            words[-1] = _Word(
                text=words[-1].text,
                x0=words[-1].x0,
                x1=right_edge,
                top=words[-1].top,
                bottom=words[-1].bottom,
                fontname=words[-1].fontname,
                size=words[-1].size,
            )
        return _Line(words=words)

    def test_short_line_with_period_creates_paragraph_break(self):
        line1 = self._make_line("End of paragraph.", right_edge=300, top=100)
        line2 = self._make_line("Start of next.", right_edge=500, top=120)
        paras = SmartPdfImporter._stitch_paragraphs([line1, line2], 612.0, 0)
        assert len(paras) == 2

    def test_full_width_lines_are_joined(self):
        line1 = self._make_line("This is a continuation", right_edge=500, top=100)
        line2 = self._make_line("of the same paragraph.", right_edge=400, top=112)
        paras = SmartPdfImporter._stitch_paragraphs([line1, line2], 612.0, 0)
        assert len(paras) == 1
        assert "continuation of the same" in paras[0].text

    def test_empty_lines_returns_empty(self):
        paras = SmartPdfImporter._stitch_paragraphs([], 612.0, 0)
        assert paras == []


# ---------------------------------------------------------------------------
# 7. Cross-page merge
# ---------------------------------------------------------------------------


class TestCrossPageMerge:
    def _make_para(self, text: str, page: int = 0) -> _Paragraph:
        w = _w(text)
        ln = _Line(words=[w])
        return _Paragraph(lines=[ln], page_index=page)

    def test_merge_when_no_terminal_punct_and_lowercase_start(self):
        p1 = self._make_para("This is a partial sentence", page=0)
        p2 = self._make_para("continued on next page.", page=1)
        result = SmartPdfImporter._cross_page_merge([[p1], [p2]])
        assert len(result) == 1
        assert "partial sentence continued" in result[0].text

    def test_no_merge_when_terminal_punct(self):
        p1 = self._make_para("Complete sentence.", page=0)
        p2 = self._make_para("New paragraph.", page=1)
        result = SmartPdfImporter._cross_page_merge([[p1], [p2]])
        assert len(result) == 2

    def test_no_merge_when_uppercase_start(self):
        p1 = self._make_para("Some text without period", page=0)
        p2 = self._make_para("New Section Title", page=1)
        result = SmartPdfImporter._cross_page_merge([[p1], [p2]])
        assert len(result) == 2

    def test_empty_pages_handled(self):
        p1 = self._make_para("Text.", page=0)
        result = SmartPdfImporter._cross_page_merge([[p1], [], []])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# 8. Heading detection
# ---------------------------------------------------------------------------


class TestHeadingDetection:
    def _make_para(self, text: str, bold: bool = False, size: float = 12.0) -> _Paragraph:
        fontname = "TimesNewRomanPS-BoldMT" if bold else "TimesNewRomanPSMT"
        w = _w(text, fontname=fontname, size=size)
        ln = _Line(words=[w])
        return _Paragraph(lines=[ln])

    def test_numbered_heading_level_1(self):
        p = self._make_para("1. Introducción")
        level = SmartPdfImporter._detect_heading("1. Introducción", p, 12.0)
        assert level == 1

    def test_numbered_heading_level_2(self):
        p = self._make_para("1.1 Propósito")
        level = SmartPdfImporter._detect_heading("1.1 Propósito", p, 12.0)
        assert level == 2

    def test_numbered_heading_level_3(self):
        p = self._make_para("2.3.1 Subdetalle")
        level = SmartPdfImporter._detect_heading("2.3.1 Subdetalle", p, 12.0)
        assert level == 3

    def test_all_caps_heading(self):
        p = self._make_para("ABSTRACT")
        level = SmartPdfImporter._detect_heading("ABSTRACT", p, 12.0)
        assert level == 1

    def test_all_caps_referencias(self):
        p = self._make_para("REFERENCIAS")
        level = SmartPdfImporter._detect_heading("REFERENCIAS", p, 12.0)
        assert level == 1

    def test_bold_short_larger_font_is_heading(self):
        p = self._make_para("Introduction", bold=True, size=14.0)
        level = SmartPdfImporter._detect_heading("Introduction", p, 12.0)
        assert level == 1

    def test_bold_short_same_size_is_level_2(self):
        p = self._make_para("Método", bold=True, size=12.0)
        level = SmartPdfImporter._detect_heading("Método", p, 12.0)
        assert level == 2

    def test_normal_body_text_is_none(self):
        p = self._make_para("This is regular body text that is not a heading at all.")
        level = SmartPdfImporter._detect_heading(
            "This is regular body text that is not a heading at all.", p, 12.0
        )
        assert level is None

    def test_very_long_text_is_none(self):
        long_text = "A" * 250
        p = self._make_para(long_text)
        level = SmartPdfImporter._detect_heading(long_text, p, 12.0)
        assert level is None


# ---------------------------------------------------------------------------
# 9. Integration: parse → ContentBlock with mocked pdfplumber
# ---------------------------------------------------------------------------


class TestParseIntegration:
    """Full-pipeline test using mock pdfplumber pages."""

    def _mock_page(self, words_data: list[dict], width: float = 612, height: float = 792):
        """Create a mock page object."""

        class MockPage:
            def __init__(self, wd, w, h):
                self._words = wd
                self.width = w
                self.height = h

            def extract_words(self, **kwargs):
                return self._words

        return MockPage(words_data, width, height)

    def test_basic_parse_produces_content_blocks(self):
        importer = SmartPdfImporter()

        page_words = [
            # Header — should be filtered
            {
                "text": "3",
                "x0": 300,
                "x1": 310,
                "top": 5,
                "bottom": 15,
                "fontname": "TimesNewRomanPSMT",
                "size": 10,
            },
            # Body text
            {
                "text": "This",
                "x0": 72,
                "x1": 100,
                "top": 100,
                "bottom": 112,
                "fontname": "TimesNewRomanPSMT",
                "size": 12,
            },
            {
                "text": "is",
                "x0": 105,
                "x1": 120,
                "top": 100,
                "bottom": 112,
                "fontname": "TimesNewRomanPSMT",
                "size": 12,
            },
            {
                "text": "body",
                "x0": 125,
                "x1": 155,
                "top": 100,
                "bottom": 112,
                "fontname": "TimesNewRomanPSMT",
                "size": 12,
            },
            {
                "text": "text.",
                "x0": 160,
                "x1": 190,
                "top": 100,
                "bottom": 112,
                "fontname": "TimesNewRomanPSMT",
                "size": 12,
            },
        ]

        mock_page = self._mock_page(page_words)

        # Monkey-patch _process_pdf to use our mock
        import types

        original_parse = importer.parse

        def patched_parse(path):
            return importer._process_pdf(types.SimpleNamespace(pages=[mock_page]))

        importer.parse = patched_parse

        from pathlib import Path

        blocks = importer.parse(Path("fake.pdf"))
        assert len(blocks) >= 1
        # The header "3" should be stripped
        full_text = " ".join(b.text for b in blocks)
        assert "3" not in full_text.split()
        assert "body" in full_text

    def test_bold_words_produce_bold_block(self):
        importer = SmartPdfImporter()

        page_words = [
            {
                "text": "Bold",
                "x0": 72,
                "x1": 100,
                "top": 100,
                "bottom": 112,
                "fontname": "TimesNewRomanPS-BoldMT",
                "size": 12,
            },
            {
                "text": "Title",
                "x0": 105,
                "x1": 140,
                "top": 100,
                "bottom": 112,
                "fontname": "TimesNewRomanPS-BoldMT",
                "size": 12,
            },
        ]

        mock_page = self._mock_page(page_words)

        import types

        def patched_parse(path):
            return importer._process_pdf(types.SimpleNamespace(pages=[mock_page]))

        importer.parse = patched_parse

        from pathlib import Path

        blocks = importer.parse(Path("fake.pdf"))
        assert len(blocks) >= 1
        assert blocks[0].is_bold is True


# ---------------------------------------------------------------------------
# 10. SemanticImporter routing
# ---------------------------------------------------------------------------


class TestSemanticImporterRouting:
    def test_pdf_extension_accepted(self):
        from apa_formatter.importers.semantic_importer import SemanticImporter

        importer = SemanticImporter()
        # Should raise ValueError about file not found, NOT about unsupported format
        with pytest.raises(ValueError, match="Archivo no encontrado"):
            importer.import_document(__import__("pathlib").Path("/tmp/nonexistent.pdf"))

    def test_unsupported_extension_rejected(self):
        from apa_formatter.importers.semantic_importer import SemanticImporter

        importer = SemanticImporter()
        with pytest.raises(ValueError, match="Formato no soportado"):
            importer.import_document(__import__("pathlib").Path("/tmp/file.txt"))

    def test_docx_still_works(self):
        from apa_formatter.importers.semantic_importer import SemanticImporter

        importer = SemanticImporter()
        # Should raise about file not opening, NOT about unsupported format
        with pytest.raises(ValueError):
            importer.import_document(__import__("pathlib").Path("/tmp/nonexistent.docx"))
