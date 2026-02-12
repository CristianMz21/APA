"""DOCX content extractor with formatting support."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from apa_formatter.models.document import APADocument, Section, TitlePage
from apa_formatter.models.enums import HeadingLevel


def extract_content_with_formatting(path: Path) -> APADocument:
    """Extract content from a .docx file, preserving basic formatting.

    Converts bold to **text** and italic to *text*.
    """
    try:
        doc = Document(str(path))
    except PackageNotFoundError:
        raise ValueError(f"Could not open file: {path}")

    # 1. Basic Metadata Extraction (Best Effort)
    title = "Untitled Document"
    authors = ["Unknown Author"]

    # Try to find title
    for para in doc.paragraphs[:5]:
        if "Title" in (para.style.name if para.style else ""):
            title = para.text.strip()
            break
        # Fallback: first centered bold paragraph
        if (
            not title and para.alignment == 1 and any(r.bold for r in para.runs)
        ):  # WD_ALIGN_PARAGRAPH.CENTER
            title = para.text.strip()

    # 2. Section Extraction
    sections: list[Section] = []
    current_heading = None
    current_content: list[str] = []

    for para in doc.paragraphs:
        style_name = ((para.style.name) if para.style else "").lower()
        text = _extract_formatted_text(para).strip()

        if not text:
            continue

        # Detect Headings
        level = _detect_heading_level(style_name, para)

        if level:
            # Save previous section
            if current_heading or current_content:
                sections.append(
                    Section(
                        heading=current_heading,
                        level=HeadingLevel.LEVEL_1,  # Flattening for now, could infer level
                        content="\n\n".join(current_content),
                    )
                )

            # Start new section
            current_heading = text.replace("**", "").replace(
                "*", ""
            )  # Strip formatting from heading title
            current_content = []
        else:
            # Body text
            # Handle lists
            if "list" in style_name:
                text = f"- {text}"

            current_content.append(text)

    # Save last section
    if current_heading or current_content:
        sections.append(
            Section(
                heading=current_heading,
                level=HeadingLevel.LEVEL_1,
                content="\n\n".join(current_content),
            )
        )

    # If no sections found, put everything in one
    if not sections and current_content:
        sections.append(
            Section(
                heading="Content",
                level=HeadingLevel.LEVEL_1,
                content="\n\n".join(current_content),
            )
        )

    return APADocument(
        title_page=TitlePage(title=title, authors=authors, affiliation="Unknown Affiliation"),
        sections=sections,
    )


def _extract_formatted_text(paragraph) -> str:
    """Convert paragraph runs to markdown text."""
    result = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue

        # Basic markdown application
        if run.bold:
            text = f"**{text}**"
        if run.italic:
            text = f"*{text}*"

        result.append(text)

    return "".join(result)


def _detect_heading_level(style_name: str, para) -> HeadingLevel | None:
    """Detect if paragraph is a heading."""
    if "heading 1" in style_name:
        return HeadingLevel.LEVEL_1
    if "heading 2" in style_name:
        return HeadingLevel.LEVEL_2
    if "heading 3" in style_name:
        return HeadingLevel.LEVEL_3

    # Heuristic for non-styled documents
    if "normal" in style_name and len(para.text) < 100:
        # Only consider it a heading if ALL text runs are bold
        runs_with_text = [r for r in para.runs if r.text.strip()]
        if runs_with_text and all(r.bold for r in runs_with_text):
            return HeadingLevel.LEVEL_1

    return None
