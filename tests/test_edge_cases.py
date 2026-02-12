"""Tests for edge cases and polish — Sprint 6."""

import pytest
from pydantic import ValidationError

from apa_formatter.error_messages import (
    format_validation_errors,
    friendly_error,
)
from apa_formatter.locale import get_locale
from apa_formatter.models.document import Author, Reference
from apa_formatter.models.enums import ReferenceType
from apa_formatter.models.reference_manager import ReferenceManager, _strip_prefix


# ─── Helpers ─────────────────────────────────────────────────────────────────

_SMITH = Author(first_name="John", last_name="Smith")
ES = get_locale("es")


def _ref(**overrides) -> Reference:
    defaults = dict(
        title="Test Title",
        ref_type=ReferenceType.BOOK,
        authors=[_SMITH],
        year=2022,
        source="Publisher",
    )
    defaults.update(overrides)
    return Reference(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# Compound Edition + Volume
# ═══════════════════════════════════════════════════════════════════════════════


class TestCompoundEditionVolume:
    """APA 7 compound descriptor: (3rd ed., Vol. 2)."""

    def test_edition_only(self):
        ref = _ref(edition="3rd")
        result = ref.format_apa()
        assert "(3rd ed.)." in result

    def test_volume_only_on_book(self):
        ref = _ref(volume="2")
        result = ref.format_apa()
        assert "(Vol. 2)." in result

    def test_edition_and_volume(self):
        ref = _ref(edition="3rd", volume="2")
        result = ref.format_apa()
        assert "(3rd ed., Vol. 2)." in result

    def test_no_edition_no_volume(self):
        ref = _ref()
        result = ref.format_apa()
        assert "*Test Title*." in result

    def test_compound_spanish(self):
        ref = _ref(edition="2a", volume="3")
        result = ref.format_apa(ES)
        assert "(2a ed., Vol. 3)." in result


# ═══════════════════════════════════════════════════════════════════════════════
# Original Year (Translated/Republished Works)
# ═══════════════════════════════════════════════════════════════════════════════


class TestOriginalYear:
    """APA 7 §10.2: Original publication year for translations."""

    def test_original_year_shows_both(self):
        ref = _ref(year=2023, original_year=1899)
        result = ref.format_apa()
        assert "(1899/2023)" in result

    def test_no_original_year(self):
        ref = _ref(year=2023)
        result = ref.format_apa()
        assert "(2023)" in result
        assert "/" not in result.split("(")[1].split(")")[0]

    def test_original_year_with_suffix(self):
        ref = _ref(year=2023, original_year=1899, year_suffix="a")
        result = ref.format_apa()
        assert "(1899/2023a)" in result

    def test_original_year_spanish(self):
        ref = _ref(year=2023, original_year=1899)
        result = ref.format_apa(ES)
        assert "(1899/2023)" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Locator Field
# ═══════════════════════════════════════════════════════════════════════════════


class TestLocator:
    """Test that the locator field is stored on Reference."""

    def test_locator_field_stored(self):
        ref = _ref(locator="para. 5")
        assert ref.locator == "para. 5"

    def test_locator_default_none(self):
        ref = _ref()
        assert ref.locator is None


# ═══════════════════════════════════════════════════════════════════════════════
# Author Prefix Sorting
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthorPrefixSorting:
    """APA 7 §9.45: Author name prefixes (de, van, von, etc.)."""

    def test_de_prefix_sorted_by_main_name(self):
        mgr = ReferenceManager()
        mgr.add(
            _ref(
                title="Alpha",
                authors=[Author(first_name="Carlos", last_name="de León")],
            )
        )
        mgr.add(
            _ref(
                title="Beta",
                authors=[Author(first_name="Amy", last_name="Adams")],
            )
        )
        mgr.sort_alphabetically()
        # Adams should come before de León (sorted by "león")
        assert mgr.references[0].authors[0].last_name == "Adams"
        assert mgr.references[1].authors[0].last_name == "de León"

    def test_van_prefix(self):
        mgr = ReferenceManager()
        mgr.add(
            _ref(
                title="Art",
                authors=[Author(first_name="Vincent", last_name="van Gogh")],
            )
        )
        mgr.add(
            _ref(
                title="Math",
                authors=[Author(first_name="Ada", last_name="Fisher")],
            )
        )
        mgr.sort_alphabetically()
        assert mgr.references[0].authors[0].last_name == "Fisher"
        assert mgr.references[1].authors[0].last_name == "van Gogh"

    def test_al_hyphen_prefix(self):
        mgr = ReferenceManager()
        mgr.add(
            _ref(
                title="Study",
                authors=[Author(first_name="Ahmad", last_name="al-Rashid")],
            )
        )
        mgr.add(
            _ref(
                title="Other",
                authors=[Author(first_name="Bob", last_name="Roberts")],
            )
        )
        mgr.sort_alphabetically()
        # al-Rashid sorts by "rashid", before "roberts"
        assert mgr.references[0].authors[0].last_name == "al-Rashid"
        assert mgr.references[1].authors[0].last_name == "Roberts"

    def test_strip_prefix_direct(self):
        assert _strip_prefix("de León") == "león"
        assert _strip_prefix("van Gogh") == "gogh"
        assert _strip_prefix("von Braun") == "braun"
        assert _strip_prefix("al-Rashid") == "rashid"
        assert _strip_prefix("Smith") == "smith"


# ═══════════════════════════════════════════════════════════════════════════════
# Error Messages
# ═══════════════════════════════════════════════════════════════════════════════


class TestFriendlyErrors:
    """Tests for user-friendly error messages."""

    def test_doi_error_english(self):
        msg = friendly_error("doi", "value_error", "en")
        assert "DOI" in msg

    def test_doi_error_spanish(self):
        msg = friendly_error("doi", "value_error", "es")
        assert "DOI" in msg
        assert "inválido" in msg

    def test_year_error_english(self):
        msg = friendly_error("year", "int_parsing", "en")
        assert "number" in msg

    def test_unknown_field_fallback(self):
        msg = friendly_error("unknown_field", "weird_error", "en")
        assert "Validation error" in msg

    def test_custom_fallback(self):
        msg = friendly_error("foo", "bar", "en", fallback="Custom message")
        assert msg == "Custom message"

    def test_format_validation_errors(self):
        errors = [
            {"loc": ["doi"], "type": "value_error", "msg": "bad doi"},
            {"loc": ["year"], "type": "int_parsing", "msg": "not an int"},
        ]
        result = format_validation_errors(errors, "en")
        assert len(result) == 2
        assert "DOI" in result[0]
        assert "number" in result[1]

    def test_format_validation_errors_spanish(self):
        errors = [
            {"loc": ["doi"], "type": "value_error", "msg": "bad doi"},
        ]
        result = format_validation_errors(errors, "es")
        assert "inválido" in result[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Unicode Handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestUnicode:
    """Ensure no crashes with non-ASCII characters."""

    def test_unicode_title(self):
        ref = _ref(title="Ñoño y la búsqueda del ü")
        result = ref.format_apa()
        assert "Ñoño" in result

    def test_unicode_author(self):
        ref = _ref(
            authors=[Author(first_name="José", last_name="García")],
        )
        result = ref.format_apa()
        assert "García" in result

    def test_unicode_roundtrip_persistence(self, tmp_path):
        from apa_formatter.persistence import load_project, save_project, Project

        ref = _ref(title="Ñoño y la búsqueda")
        p = Project(title="Ünïcödé", references=[ref])
        dest = tmp_path / "unicode.json"
        save_project(p, dest)
        loaded = load_project(dest)
        assert loaded.title == "Ünïcödé"
        assert loaded.references[0].title == "Ñoño y la búsqueda"


# ═══════════════════════════════════════════════════════════════════════════════
# DOI Validation Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestDOIEdgeCases:
    """Additional DOI validation edge cases."""

    def test_doi_with_special_chars(self):
        ref = _ref(doi="10.1000/test-doi_v1.2(3)")
        assert ref.doi == "10.1000/test-doi_v1.2(3)"

    def test_doi_with_dx_doi_prefix(self):
        ref = _ref(doi="https://dx.doi.org/10.1000/test")
        assert ref.doi == "10.1000/test"

    def test_doi_http_prefix(self):
        ref = _ref(doi="http://doi.org/10.1000/test")
        assert ref.doi == "10.1000/test"

    def test_doi_invalid_raises(self):
        with pytest.raises(ValidationError):
            _ref(doi="not-a-doi")

    def test_doi_none_is_valid(self):
        ref = _ref(doi=None)
        assert ref.doi is None
