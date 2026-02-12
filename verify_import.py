import sys
from pathlib import Path

# Add src to python path so we can import apa_formatter
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT / "src"))

from apa_formatter.importers.semantic_importer import SemanticImporter


def verify_import(filepath: str):
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {path}")
        return

    print("Importing file:", path)
    importer = SemanticImporter()
    try:
        doc = importer.import_document(path, use_ai=False)
    except Exception as e:
        print(f"Import failed: {e}")
        import traceback

        traceback.print_exc()
        return

    print("\n--- Title Page ---")
    if doc.title_page:
        print(f"Title: {doc.title_page.title}")
        print(f"Authors: {doc.title_page.authors}")
        print(f"Affiliation: {doc.title_page.affiliation}")
    else:
        print("No Title Page Detected")

    print("\n--- Abstract ---")
    if doc.abstract:
        print(f"Abstract Length: {len(doc.abstract)} chars")
        print(f"Preview: {doc.abstract[:100]}...")
    else:
        print("No Abstract")

    print("\n--- Sections ---")
    for sec in doc.body_sections:
        print(f"Section: {sec.heading} (Level {sec.level})")
        # Subsections are nested in sections, but SemanticDocument might flatten them or structure them?
        # SemanticDocument.sections is list[SectionData]
        if hasattr(sec, "subsections") and sec.subsections:
            for sub in sec.subsections:
                print(f"  Subsection: {sub.heading}")

    print("\n--- References ---")
    print(f"Count: {len(doc.references_parsed)}")
    for ref in doc.references_parsed:
        # Reference object might differ
        print(f"- {ref}")


if __name__ == "__main__":
    verify_import("/home/mackroph/Projectos/Learning/APA/Examples/informe_apa.docx")
