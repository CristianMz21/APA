"""APA 7 document renderer — converts APADocument into a QTextDocument.

This module is the bridge between the Pydantic domain models and the
Qt rich-text engine.  Every APA 7 formatting rule (heading hierarchy,
double spacing, hanging indent for references, etc.) is expressed through
QTextBlockFormat / QTextCharFormat applied via a QTextCursor.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)

from apa_formatter.models.document import APADocument, Section
from apa_formatter.models.enums import HeadingLevel

# ---------------------------------------------------------------------------
# APA 7 constants (at 96 DPI: 1 cm ≈ 37.8 px, 1.27 cm ≈ 48 px)
# ---------------------------------------------------------------------------
INDENT_PX = 48  # 1.27 cm — first-line / hanging indent
LINE_HEIGHT_DOUBLE = 200  # 200 % = double spacing
FONT_SIZE_BODY_PT = 12


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_to_qtextdocument(doc: APADocument) -> QTextDocument:
    """Build a fully-formatted QTextDocument from an APADocument model."""
    qt_doc = QTextDocument()
    qt_doc.setUndoRedoEnabled(False)
    cursor = QTextCursor(qt_doc)

    # Base character format
    base_char = _base_char_format(doc.font.value, FONT_SIZE_BODY_PT)

    # Base block format (double-spaced, left-aligned)
    base_block = QTextBlockFormat()
    base_block.setLineHeight(LINE_HEIGHT_DOUBLE, 1)  # 1 = ProportionalHeight

    # 1️⃣ Title page
    _render_title_page(cursor, doc, base_char, base_block)

    # 2️⃣ Abstract (if present)
    if doc.abstract:
        _render_abstract(cursor, doc, base_char, base_block)

    # 3️⃣  Body sections
    for section in doc.sections:
        _render_section(cursor, section, base_char, base_block)

    # 4️⃣  References
    if doc.references:
        _render_references(cursor, doc, base_char, base_block)

    qt_doc.setUndoRedoEnabled(True)
    return qt_doc


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _base_char_format(family: str, size: int) -> QTextCharFormat:
    fmt = QTextCharFormat()
    font = QFont(family, size)
    fmt.setFont(font)
    return fmt


def _centered_bold_heading(
    cursor: QTextCursor,
    text: str,
    base_char: QTextCharFormat,
    base_block: QTextBlockFormat,
) -> None:
    """Insert a centred bold heading (used for title, "Abstract", "Referencias")."""
    block = QTextBlockFormat(base_block)
    block.setAlignment(Qt.AlignmentFlag.AlignCenter)

    char = QTextCharFormat(base_char)
    char.setFontWeight(QFont.Weight.Bold)

    cursor.insertBlock(block, char)
    cursor.insertText(text)


# ---- Title page -----------------------------------------------------------


def _render_title_page(
    cursor: QTextCursor,
    doc: APADocument,
    base_char: QTextCharFormat,
    base_block: QTextBlockFormat,
) -> None:
    center_block = QTextBlockFormat(base_block)
    center_block.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # Title — bold, centred
    title_char = QTextCharFormat(base_char)
    title_char.setFontWeight(QFont.Weight.Bold)

    # First block — no insertBlock() needed (cursor is at doc start)
    cursor.setBlockFormat(center_block)
    cursor.setCharFormat(title_char)
    cursor.insertText(doc.title_page.title)

    # Authors
    cursor.insertBlock(center_block, base_char)
    cursor.insertText(", ".join(doc.title_page.authors))

    # Affiliation
    cursor.insertBlock(center_block, base_char)
    cursor.insertText(doc.title_page.affiliation)

    # Student-specific fields
    tp = doc.title_page
    if tp.course:
        cursor.insertBlock(center_block, base_char)
        cursor.insertText(tp.course)
    if tp.instructor:
        cursor.insertBlock(center_block, base_char)
        cursor.insertText(tp.instructor)
    if tp.due_date:
        cursor.insertBlock(center_block, base_char)
        cursor.insertText(tp.due_date.strftime("%d de %B de %Y"))


# ---- Abstract -------------------------------------------------------------


def _render_abstract(
    cursor: QTextCursor,
    doc: APADocument,
    base_char: QTextCharFormat,
    base_block: QTextBlockFormat,
) -> None:
    # Page break before abstract
    page_break = QTextBlockFormat(base_block)
    page_break.setPageBreakPolicy(QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore)
    cursor.insertBlock(page_break, base_char)

    _centered_bold_heading(cursor, "Resumen", base_char, base_block)

    # Abstract body — no first-line indent per APA 7
    body_block = QTextBlockFormat(base_block)
    body_block.setTextIndent(0)
    cursor.insertBlock(body_block, base_char)
    cursor.insertText(doc.abstract)

    # Keywords
    if doc.keywords:
        kw_block = QTextBlockFormat(base_block)
        kw_block.setTextIndent(INDENT_PX)
        cursor.insertBlock(kw_block)

        kw_label = QTextCharFormat(base_char)
        kw_label.setFontItalic(True)
        cursor.setCharFormat(kw_label)
        cursor.insertText("Palabras clave: ")

        cursor.setCharFormat(base_char)
        cursor.insertText(", ".join(doc.keywords))


# ---- Sections -------------------------------------------------------------

# Maps HeadingLevel → (bold, italic, centred, inline-with-text)
_HEADING_STYLES: dict[HeadingLevel, tuple[bool, bool, bool, bool]] = {
    HeadingLevel.LEVEL_1: (True, False, True, False),
    HeadingLevel.LEVEL_2: (True, False, False, False),
    HeadingLevel.LEVEL_3: (True, True, False, False),
    HeadingLevel.LEVEL_4: (True, False, False, True),
    HeadingLevel.LEVEL_5: (True, True, False, True),
}


def _render_section(
    cursor: QTextCursor,
    section: Section,
    base_char: QTextCharFormat,
    base_block: QTextBlockFormat,
    *,
    depth: int = 0,
) -> None:
    bold, italic, centred, inline = _HEADING_STYLES.get(section.level, (True, False, False, False))

    # ---- Heading ---
    if section.heading:
        h_block = QTextBlockFormat(base_block)
        if centred:
            h_block.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elif section.level in (HeadingLevel.LEVEL_4, HeadingLevel.LEVEL_5):
            h_block.setTextIndent(INDENT_PX)

        h_char = QTextCharFormat(base_char)
        if bold:
            h_char.setFontWeight(QFont.Weight.Bold)
        if italic:
            h_char.setFontItalic(True)

        cursor.insertBlock(h_block, h_char)
        heading_text = section.heading
        if inline:
            heading_text += "."
        cursor.insertText(heading_text)

        # For inline headings (L4/L5), body text continues on the same line

        if inline and section.content:
            cursor.insertText("  ")
            # cursor.setCharFormat(base_char) -> handled by markdown renderer
            _render_markdown_text(cursor, section.content, base_char)
        elif section.content:
            # Body paragraph with first-line indent
            body_block = QTextBlockFormat(base_block)
            body_block.setTextIndent(INDENT_PX)
            cursor.insertBlock(body_block, base_char)
            # cursor.insertText(section.content) -> handled by markdown renderer
            _render_markdown_text(cursor, section.content, base_char)
    elif section.content:
        body_block = QTextBlockFormat(base_block)
        body_block.setTextIndent(INDENT_PX)
        cursor.insertBlock(body_block, base_char)
        # cursor.insertText(section.content)
        _render_markdown_text(cursor, section.content, base_char)

    # Recurse into subsections
    for sub in section.subsections:
        _render_section(cursor, sub, base_char, base_block, depth=depth + 1)


# ---- References -----------------------------------------------------------


def _render_references(
    cursor: QTextCursor,
    doc: APADocument,
    base_char: QTextCharFormat,
    base_block: QTextBlockFormat,
) -> None:
    # Page break before references
    page_break = QTextBlockFormat(base_block)
    page_break.setPageBreakPolicy(QTextBlockFormat.PageBreakFlag.PageBreak_AlwaysBefore)
    cursor.insertBlock(page_break, base_char)

    _centered_bold_heading(cursor, "Referencias", base_char, base_block)

    # Hanging indent:  left margin pushed in, first line pulled back
    hanging = QTextBlockFormat(base_block)
    hanging.setLeftMargin(INDENT_PX)
    hanging.setTextIndent(-INDENT_PX)

    for ref in doc.references:
        cursor.insertBlock(hanging, base_char)

        # We need to parse the formatted string to apply italic to titles
        ref_text = ref.format_apa()
        _render_markdown_text(cursor, ref_text, base_char)


def _render_markdown_text(cursor: QTextCursor, text: str, base_char: QTextCharFormat) -> None:
    """Render text with basic markdown support (**bold**, *italic*)."""
    import re

    # Pattern to match **bold** or *italic*
    # Group 1: **bold**
    # Group 2: *italic*
    pattern = re.compile(r"(\*\*[^*]+\*\*)|(\*[^*]+\*)")

    last_pos = 0
    for match in pattern.finditer(text):
        # Text before match
        prefix = text[last_pos : match.start()]
        if prefix:
            cursor.setCharFormat(base_char)
            cursor.insertText(prefix)

        # Match content
        content = match.group()
        fmt = QTextCharFormat(base_char)

        if content.startswith("**"):
            fmt.setFontWeight(QFont.Weight.Bold)
            clean_text = content[2:-2]
        else:
            fmt.setFontItalic(True)
            clean_text = content[1:-1]

        cursor.setCharFormat(fmt)
        cursor.insertText(clean_text)

        last_pos = match.end()

    # Remaining text
    suffix = text[last_pos:]
    if suffix:
        cursor.setCharFormat(base_char)
        cursor.insertText(suffix)
