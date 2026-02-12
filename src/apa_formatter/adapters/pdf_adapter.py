"""PDF adapter for APA 7 document generation using fpdf2."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from apa_formatter.adapters.base import BaseAdapter
from apa_formatter.domain.models.document import APADocument, Section
from apa_formatter.domain.models.enums import DocumentVariant, HeadingLevel
from apa_formatter.rules.constants import (
    FIRST_LINE_INDENT_INCHES,
    HEADING_STYLES,
    LINE_SPACING,
    MARGIN_INCHES,
    REFERENCES_HEADING,
    TITLE_PAGE_BLANK_LINES_BEFORE_TITLE,
)


# Conversion helpers
_IN_TO_MM = 25.4


def _in2mm(inches: float) -> float:
    return inches * _IN_TO_MM


class APAPDF(FPDF):
    """Custom FPDF subclass with APA 7 headers and footers."""

    def __init__(self, font_name: str, font_size: int, running_head: str | None = None) -> None:
        super().__init__(orientation="P", unit="mm", format="Letter")
        self._font_name = font_name
        self._font_size = font_size
        self._running_head = running_head

    def header(self) -> None:
        """APA 7 header: optional running head + page number (top-right)."""
        self.set_font(self._font_name, "", self._font_size)
        header_text = ""
        if self._running_head:
            header_text = self._running_head.upper() + "   "
        # Right-aligned page number
        self.cell(
            0, 10, header_text + str(self.page_no()), align="R", new_x="LMARGIN", new_y="NEXT"
        )

    def footer(self) -> None:
        """APA 7 has no footer content (page number is in the header)."""
        pass


class PdfAdapter(BaseAdapter):
    """Generate APA 7 formatted PDF documents using fpdf2."""

    def __init__(self, document: APADocument, config=None, user_settings=None) -> None:
        super().__init__(document, config=config)
        self._font_spec = self._get_font_spec()
        self._setup_font_mapping()

        running_head = None
        if (
            document.title_page.variant == DocumentVariant.PROFESSIONAL
            and document.title_page.running_head
        ):
            running_head = document.title_page.running_head

        self._pdf = APAPDF(
            font_name=self._mapped_font,
            font_size=self._font_spec.size_pt,
            running_head=running_head,
        )
        self._line_h = self._font_spec.size_pt * LINE_SPACING * 0.3528  # pt to mm, double-spaced

    def _setup_font_mapping(self) -> None:
        """Map APA font names to fpdf2 built-in fonts."""
        # fpdf2 built-in fonts: Helvetica, Times, Courier
        font_map = {
            "Times New Roman": "Times",
            "Arial": "Helvetica",
            "Calibri": "Helvetica",
            "Georgia": "Times",
        }
        self._mapped_font = font_map.get(self._font_spec.name, "Times")

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _sanitize(self, text: str) -> str:
        """Replace characters not supported by standard PDF fonts (Latin-1)."""
        if not text:
            return ""
        # Common replacements for "smart" punctuation
        replacements = {
            "\u2013": "-",  # en-dash
            "\u2014": "--",  # em-dash
            "\u2018": "'",  # left single quote
            "\u2019": "'",  # right single quote
            "\u201c": '"',  # left double quote
            "\u201d": '"',  # right double quote
            "\u2026": "...",  # ellipsis
        }
        for char, repl in replacements.items():
            text = text.replace(char, repl)

        # Fallback: encode to latin-1, replace errors with '?'
        return text.encode("latin-1", "replace").decode("latin-1")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, output_path: Path) -> Path:
        """Build the complete APA 7 PDF and save to *output_path*."""
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".pdf")

        margin = _in2mm(MARGIN_INCHES)
        self._pdf.set_margins(margin, margin, margin)
        self._pdf.set_auto_page_break(auto=True, margin=margin)

        self._build_title_page()

        if self.doc.abstract:
            self._build_abstract()

        self._build_body()

        if self.doc.references:
            self._build_references()

        if self.doc.appendices:
            self._build_appendices()

        self._pdf.output(str(output_path))
        return output_path

    # ------------------------------------------------------------------
    # Title Page
    # ------------------------------------------------------------------

    def _build_title_page(self) -> None:
        tp = self.doc.title_page
        self._pdf.add_page()

        # Push title down ~1/3 of page
        for _ in range(TITLE_PAGE_BLANK_LINES_BEFORE_TITLE):
            self._pdf.ln(self._line_h)

        # Title — bold, centered
        self._pdf.set_font(self._mapped_font, "B", self._font_spec.size_pt)
        self._pdf.cell(
            0, self._line_h, self._sanitize(tp.title), align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self._pdf.ln(self._line_h)

        # Authors
        self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)
        authors_text = ", ".join(tp.authors[:-1])
        if len(tp.authors) > 1:
            authors_text += f", and {tp.authors[-1]}"
        else:
            authors_text = tp.authors[0]
        self._pdf.cell(
            0, self._line_h, self._sanitize(authors_text), align="C", new_x="LMARGIN", new_y="NEXT"
        )

        # Affiliation
        self._pdf.cell(
            0,
            self._line_h,
            self._sanitize(tp.affiliation),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Student fields
        if tp.variant == DocumentVariant.STUDENT:
            if tp.course:
                self._pdf.cell(
                    0,
                    self._line_h,
                    self._sanitize(tp.course),
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
            if tp.instructor:
                self._pdf.cell(
                    0,
                    self._line_h,
                    self._sanitize(tp.instructor),
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
            if tp.due_date:
                date_str = tp.due_date.strftime("%B %d, %Y")
                self._pdf.cell(
                    0,
                    self._line_h,
                    self._sanitize(date_str),
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

    # ------------------------------------------------------------------
    # Abstract
    # ------------------------------------------------------------------

    def _build_abstract(self) -> None:
        self._pdf.add_page()

        # "Abstract" heading
        self._pdf.set_font(self._mapped_font, "B", self._font_spec.size_pt)
        self._pdf.cell(0, self._line_h, "Abstract", align="C", new_x="LMARGIN", new_y="NEXT")

        # Abstract text (no indent)
        self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)
        self._pdf.multi_cell(0, self._line_h, self._sanitize(self.doc.abstract or ""))

        # Keywords
        if self.doc.keywords:
            indent = _in2mm(FIRST_LINE_INDENT_INCHES)
            self._pdf.set_x(self._pdf.l_margin + indent)
            self._pdf.set_font(self._mapped_font, "I", self._font_spec.size_pt)
            self._pdf.write(self._line_h, "Keywords: ")
            self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)
            self._pdf.write(self._line_h, self._sanitize(", ".join(self.doc.keywords)))
            self._pdf.ln(self._line_h)

    # ------------------------------------------------------------------
    # Body
    # ------------------------------------------------------------------

    def _build_body(self) -> None:
        self._pdf.add_page()
        for section in self.doc.sections:
            self._render_section(section)

    def _render_section(self, section: Section) -> None:
        if section.heading:
            self._add_heading(section.heading, section.level)

        if section.content:
            style = HEADING_STYLES.get(section.level.value)
            if style and style.inline and section.heading:
                # Content was handled inline in _add_heading
                pass
            else:
                paragraphs = section.content.split("\n\n")
                for para_text in paragraphs:
                    if para_text.strip():
                        self._add_body_paragraph(para_text.strip())

        for sub in section.subsections:
            self._render_section(sub)

    def _add_heading(self, text: str, level: HeadingLevel) -> None:
        style = HEADING_STYLES[level.value]

        font_style = ""
        if style.bold:
            font_style += "B"
        if style.italic:
            font_style += "I"

        self._pdf.set_font(self._mapped_font, font_style, self._font_spec.size_pt)

        if style.indent:
            indent = _in2mm(FIRST_LINE_INDENT_INCHES)
            self._pdf.set_x(self._pdf.l_margin + indent)

        if style.centered:
            align = "C"
        else:
            align = "L"

        if style.inline:
            # Heading text with period, then content continues on same line
            self._pdf.write(self._line_h, self._sanitize(text + ". "))
            self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)
        else:
            self._pdf.cell(
                0, self._line_h, self._sanitize(text), align=align, new_x="LMARGIN", new_y="NEXT"
            )

    def _add_body_paragraph(self, text: str) -> None:
        """Add a body paragraph with first-line indent."""
        self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)
        indent = _in2mm(FIRST_LINE_INDENT_INCHES)

        # First-line indent: write spaces then multi_cell
        x_start = self._pdf.l_margin + indent
        self._pdf.set_x(x_start)
        # Use multi_cell for wrapping, but only indent the first line
        self._pdf.multi_cell(0, self._line_h, self._sanitize(text))

    # ------------------------------------------------------------------
    # References
    # ------------------------------------------------------------------

    def _build_references(self) -> None:
        self._pdf.add_page()

        # "References" heading
        self._pdf.set_font(self._mapped_font, "B", self._font_spec.size_pt)
        self._pdf.cell(
            0, self._line_h, REFERENCES_HEADING, align="C", new_x="LMARGIN", new_y="NEXT"
        )

        sorted_refs = sorted(
            self.doc.references,
            key=lambda r: (
                getattr(r.authors[0], "last_name", getattr(r.authors[0], "name", "")).lower()
                if r.authors
                else ""
            ),
        )

        self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)

        for ref in sorted_refs:
            ref_text = ref.format_apa().replace("*", "")  # Remove italic markers for PDF
            self._pdf.set_x(self._pdf.l_margin)
            self._pdf.multi_cell(
                w=self._pdf.w - self._pdf.l_margin - self._pdf.r_margin,
                h=self._line_h,
                text=self._sanitize(ref_text),
            )

    # ------------------------------------------------------------------
    # Appendices
    # ------------------------------------------------------------------

    def _build_appendices(self) -> None:
        for i, appendix in enumerate(self.doc.appendices):
            self._pdf.add_page()
            label = f"Appendix {chr(65 + i)}" if len(self.doc.appendices) > 1 else "Appendix"

            self._pdf.set_font(self._mapped_font, "B", self._font_spec.size_pt)
            self._pdf.cell(0, self._line_h, label, align="C", new_x="LMARGIN", new_y="NEXT")

            if appendix.heading:
                self._pdf.cell(
                    0,
                    self._line_h,
                    self._sanitize(appendix.heading),
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

            if appendix.content:
                self._pdf.set_font(self._mapped_font, "", self._font_spec.size_pt)
                self._add_body_paragraph(appendix.content)
