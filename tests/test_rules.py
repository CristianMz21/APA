"""Tests for APA 7 rules engine constants."""

from apa_formatter.rules.constants import (
    FIRST_LINE_INDENT_INCHES,
    FONT_SPECS,
    HANGING_INDENT_INCHES,
    HEADING_STYLES,
    LINE_SPACING,
    MARGIN_INCHES,
    REFERENCES_HEADING,
    SPACE_AFTER_PT,
    SPACE_BEFORE_PT,
    TITLE_PAGE_BLANK_LINES_BEFORE_TITLE,
)
from apa_formatter.models.enums import FontChoice


class TestPageLayout:
    def test_margin_is_one_inch(self):
        assert MARGIN_INCHES == 1.0

    def test_line_spacing_is_double(self):
        assert LINE_SPACING == 2.0

    def test_first_line_indent(self):
        assert FIRST_LINE_INDENT_INCHES == 0.5

    def test_hanging_indent(self):
        assert HANGING_INDENT_INCHES == 0.5

    def test_no_space_before_after(self):
        assert SPACE_BEFORE_PT == 0
        assert SPACE_AFTER_PT == 0


class TestFonts:
    def test_times_new_roman(self):
        spec = FONT_SPECS[FontChoice.TIMES_NEW_ROMAN]
        assert spec.name == "Times New Roman"
        assert spec.size_pt == 12

    def test_calibri(self):
        spec = FONT_SPECS[FontChoice.CALIBRI]
        assert spec.name == "Calibri"
        assert spec.size_pt == 11

    def test_arial(self):
        spec = FONT_SPECS[FontChoice.ARIAL]
        assert spec.name == "Arial"
        assert spec.size_pt == 11

    def test_georgia(self):
        spec = FONT_SPECS[FontChoice.GEORGIA]
        assert spec.name == "Georgia"
        assert spec.size_pt == 11

    def test_all_fonts_have_specs(self):
        for choice in FontChoice:
            assert choice in FONT_SPECS


class TestHeadingStyles:
    def test_five_levels_exist(self):
        assert len(HEADING_STYLES) == 5
        for level in range(1, 6):
            assert level in HEADING_STYLES

    def test_level_1_centered_bold(self):
        style = HEADING_STYLES[1]
        assert style.centered is True
        assert style.bold is True
        assert style.italic is False
        assert style.inline is False

    def test_level_2_left_bold(self):
        style = HEADING_STYLES[2]
        assert style.centered is False
        assert style.bold is True
        assert style.italic is False

    def test_level_3_left_bold_italic(self):
        style = HEADING_STYLES[3]
        assert style.centered is False
        assert style.bold is True
        assert style.italic is True

    def test_level_4_inline_bold(self):
        style = HEADING_STYLES[4]
        assert style.inline is True
        assert style.bold is True
        assert style.indent is True

    def test_level_5_inline_bold_italic(self):
        style = HEADING_STYLES[5]
        assert style.inline is True
        assert style.bold is True
        assert style.italic is True
        assert style.indent is True


class TestOtherConstants:
    def test_references_heading(self):
        assert isinstance(REFERENCES_HEADING, str)
        assert len(REFERENCES_HEADING) > 0

    def test_title_page_blank_lines(self):
        assert isinstance(TITLE_PAGE_BLANK_LINES_BEFORE_TITLE, int)
        assert TITLE_PAGE_BLANK_LINES_BEFORE_TITLE > 0
