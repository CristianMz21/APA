"""Tests for internationalization (i18n) support — Sprint 4."""

from apa_formatter.locale import get_locale
from apa_formatter.models.document import Author, Citation, Reference
from apa_formatter.models.enums import CitationType, ReferenceType
from apa_formatter.models.reference_manager import ReferenceManager


# ─── Locale Loader ──────────────────────────────────────────────────────────


class TestLocaleLoader:
    """Tests for the locale loading infrastructure."""

    def test_load_english(self):
        loc = get_locale("en")
        assert loc["and"] == "and"
        assert loc["nd"] == "n.d."
        assert loc["retrieved"] == "Retrieved"

    def test_load_spanish(self):
        loc = get_locale("es")
        assert loc["and"] == "y"
        assert loc["nd"] == "s.f."
        assert loc["retrieved"] == "Recuperado"
        assert loc["as_cited_in"] == "como se citó en"
        assert loc["personal_communication"] == "comunicación personal"

    def test_unknown_locale_falls_back_to_english(self):
        loc = get_locale("xx")
        assert loc["and"] == "and"
        assert loc["nd"] == "n.d."

    def test_locale_is_cached(self):
        """Calling get_locale twice returns the same dict object (LRU cache)."""
        a = get_locale("en")
        b = get_locale("en")
        assert a is b

    def test_all_keys_present_in_both_locales(self):
        """en.json and es.json must have matching key sets."""
        en = get_locale("en")
        es = get_locale("es")
        assert set(en.keys()) == set(es.keys())


# ─── Helpers ─────────────────────────────────────────────────────────────────

ES = get_locale("es")
EN = get_locale("en")

_SMITH = Author(first_name="John", last_name="Smith")
_JONES = Author(first_name="Amy", last_name="Jones")


def _ref(**overrides) -> Reference:
    """Create a minimal reference with sensible defaults."""
    defaults = dict(
        title="Test Title",
        ref_type=ReferenceType.BOOK,
        authors=[_SMITH],
        year=2022,
        source="Publisher",
    )
    defaults.update(overrides)
    return Reference(**defaults)


# ─── Reference.format_apa() with locale ─────────────────────────────────────


class TestReferenceLocale:
    """Test that Reference.format_apa() respects locale strings."""

    def test_no_date_english(self):
        ref = _ref(year=None)
        result = ref.format_apa()
        assert "(n.d.)." in result

    def test_no_date_spanish(self):
        ref = _ref(year=None)
        result = ref.format_apa(ES)
        assert "(s.f.)." in result

    def test_book_edition_english(self):
        ref = _ref(edition="2nd")
        result = ref.format_apa()
        assert "(2nd ed.)." in result

    def test_book_edition_spanish(self):
        ref = _ref(edition="2a")
        result = ref.format_apa(ES)
        assert "(2a ed.)." in result

    def test_book_chapter_english(self):
        ref = _ref(
            ref_type=ReferenceType.BOOK_CHAPTER,
            editors=[Author(first_name="Anna", last_name="Lee")],
            pages="10-20",
        )
        result = ref.format_apa()
        assert "In" in result
        assert "(Eds.)," in result
        assert "(pp. 10-20)." in result

    def test_book_chapter_spanish(self):
        ref = _ref(
            ref_type=ReferenceType.BOOK_CHAPTER,
            editors=[Author(first_name="Anna", last_name="Lee")],
            pages="10-20",
        )
        result = ref.format_apa(ES)
        assert "En" in result
        assert "(Eds.)," in result
        assert "(pp. 10-20)." in result

    def test_conference_default_media_english(self):
        ref = _ref(ref_type=ReferenceType.CONFERENCE_PAPER)
        result = ref.format_apa()
        assert "[Conference presentation]." in result

    def test_conference_default_media_spanish(self):
        ref = _ref(ref_type=ReferenceType.CONFERENCE_PAPER)
        result = ref.format_apa(ES)
        assert "[Presentación de conferencia]." in result

    def test_dissertation_default_english(self):
        ref = _ref(ref_type=ReferenceType.DISSERTATION, university="MIT")
        result = ref.format_apa()
        assert "[Doctoral dissertation, MIT]." in result

    def test_dissertation_default_spanish(self):
        ref = _ref(ref_type=ReferenceType.DISSERTATION, university="SENA")
        result = ref.format_apa(ES)
        assert "[Tesis doctoral, SENA]." in result

    def test_report_number_english(self):
        ref = _ref(ref_type=ReferenceType.REPORT, report_number="42")
        result = ref.format_apa()
        assert "(Report No. 42)." in result

    def test_report_number_spanish(self):
        ref = _ref(ref_type=ReferenceType.REPORT, report_number="42")
        result = ref.format_apa(ES)
        assert "(Informe No. 42)." in result

    def test_webpage_retrieval_english(self):
        from datetime import date

        ref = _ref(
            ref_type=ReferenceType.WEBPAGE,
            retrieval_date=date(2024, 3, 15),
            url="https://example.com",
        )
        result = ref.format_apa()
        assert "Retrieved March 15, 2024, from" in result

    def test_webpage_retrieval_spanish(self):
        from datetime import date

        ref = _ref(
            ref_type=ReferenceType.WEBPAGE,
            retrieval_date=date(2024, 3, 15),
            url="https://example.com",
        )
        result = ref.format_apa(ES)
        assert "Recuperado" in result
        assert "de" in result

    def test_legal_no_year_english(self):
        ref = _ref(
            ref_type=ReferenceType.LEGAL,
            year=None,
            source="U.S.C.",
            volume="42",
        )
        result = ref.format_apa()
        assert "(n.d.)." in result

    def test_legal_no_year_spanish(self):
        ref = _ref(
            ref_type=ReferenceType.LEGAL,
            year=None,
            source="U.S.C.",
            volume="42",
        )
        result = ref.format_apa(ES)
        assert "(s.f.)." in result

    def test_default_locale_matches_no_locale(self):
        """Passing EN locale must produce the same result as no locale."""
        ref = _ref()
        assert ref.format_apa() == ref.format_apa(EN)


# ─── Citation.format_apa() with locale ──────────────────────────────────────


class TestCitationLocale:
    """Test that Citation.format_apa() respects locale strings."""

    def test_single_author_no_date_english(self):
        c = Citation(authors=["Smith"])
        assert c.format_apa() == "(Smith, n.d.)"

    def test_single_author_no_date_spanish(self):
        c = Citation(authors=["Smith"])
        assert c.format_apa(ES) == "(Smith, s.f.)"

    def test_two_authors_narrative_english(self):
        c = Citation(
            authors=["Smith", "Jones"],
            year=2020,
            citation_type=CitationType.NARRATIVE,
        )
        assert c.format_apa() == "Smith and Jones (2020)"

    def test_two_authors_narrative_spanish(self):
        c = Citation(
            authors=["Smith", "Jones"],
            year=2020,
            citation_type=CitationType.NARRATIVE,
        )
        assert c.format_apa(ES) == "Smith y Jones (2020)"

    def test_three_authors_et_al(self):
        c = Citation(authors=["Smith", "Jones", "Lee"], year=2020)
        # et al. is the same in both EN and ES
        assert c.format_apa() == "(Smith et al., 2020)"
        assert c.format_apa(ES) == "(Smith et al., 2020)"

    def test_page_english(self):
        c = Citation(authors=["Smith"], year=2020, page="15")
        assert c.format_apa() == "(Smith, 2020, p. 15)"

    def test_page_spanish(self):
        c = Citation(authors=["Smith"], year=2020, page="15")
        assert c.format_apa(ES) == "(Smith, 2020, p. 15)"

    def test_secondary_citation_english(self):
        c = Citation(
            authors=["Freud"],
            year=1923,
            is_secondary=True,
            secondary_author="Smith",
            secondary_year=2020,
        )
        assert c.format_apa() == "(Freud, 1923, as cited in Smith, 2020)"

    def test_secondary_citation_spanish(self):
        c = Citation(
            authors=["Freud"],
            year=1923,
            is_secondary=True,
            secondary_author="Smith",
            secondary_year=2020,
        )
        assert c.format_apa(ES) == "(Freud, 1923, como se citó en Smith, 2020)"

    def test_personal_communication_english(self):
        c = Citation(
            citation_type=CitationType.PERSONAL_COMMUNICATION,
            authors=["J. Smith"],
            communication_date="March 15, 2024",
        )
        assert c.format_apa() == "(J. Smith, personal communication, March 15, 2024)"

    def test_personal_communication_spanish(self):
        c = Citation(
            citation_type=CitationType.PERSONAL_COMMUNICATION,
            authors=["J. Smith"],
            communication_date="15 de marzo de 2024",
        )
        assert c.format_apa(ES) == "(J. Smith, comunicación personal, 15 de marzo de 2024)"

    def test_default_locale_matches_no_locale(self):
        c = Citation(authors=["Smith"], year=2020)
        assert c.format_apa() == c.format_apa(EN)


# ─── ReferenceManager with locale ───────────────────────────────────────────


class TestReferenceManagerLocale:
    """Test ReferenceManager.format_reference_list() respects locale."""

    def test_format_list_with_spanish(self):
        mgr = ReferenceManager()
        mgr.add(_ref(year=None))
        result = mgr.format_reference_list(ES)
        assert "(s.f.)." in result

    def test_format_list_english_same_as_default(self):
        mgr = ReferenceManager()
        mgr.add(_ref())
        assert mgr.format_reference_list() == mgr.format_reference_list(EN)
