"""Tests for Sprint 2: year disambiguation, secondary citations, personal communications."""


from apa_formatter.models.document import (
    Author,
    Citation,
    GroupAuthor,
    Reference,
)
from apa_formatter.models.enums import CitationType, ReferenceType
from apa_formatter.models.reference_manager import ReferenceManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _author(last="Smith", first="John", mid=None):
    return Author(last_name=last, first_name=first, middle_initial=mid)


def _ref(authors=None, year=2020, title="Test", ref_type=ReferenceType.BOOK, **kw):
    return Reference(
        ref_type=ref_type,
        authors=authors or [_author()],
        year=year,
        title=title,
        **kw,
    )


# ===========================================================================
# Year Disambiguation (APA 7 §8.19)
# ===========================================================================


class TestYearDisambiguation:
    """ReferenceManager.disambiguate_years() assigns a/b/c suffixes."""

    def test_no_collision_no_suffix(self):
        mgr = ReferenceManager()
        mgr.add(_ref(year=2020, title="Alpha"))
        mgr.add(_ref(year=2021, title="Beta"))
        assert all(r.year_suffix is None for r in mgr.references)

    def test_same_author_same_year_gets_suffixes(self):
        mgr = ReferenceManager()
        mgr.add(_ref(year=2020, title="Beta"))
        mgr.add(_ref(year=2020, title="Alpha"))
        # After disambiguation, sorted by title: Alpha=a, Beta=b
        suffixes = sorted(r.year_suffix for r in mgr.references)
        assert suffixes == ["a", "b"]

    def test_three_works_same_author_year(self):
        mgr = ReferenceManager()
        mgr.add(_ref(year=2020, title="Charlie"))
        mgr.add(_ref(year=2020, title="Alpha"))
        mgr.add(_ref(year=2020, title="Bravo"))
        suffixes = sorted(r.year_suffix for r in mgr.references)
        assert suffixes == ["a", "b", "c"]

    def test_different_authors_same_year_no_suffix(self):
        mgr = ReferenceManager()
        mgr.add(_ref(authors=[_author("Smith", "John")], year=2020, title="A"))
        mgr.add(_ref(authors=[_author("Jones", "Jane")], year=2020, title="B"))
        assert all(r.year_suffix is None for r in mgr.references)

    def test_suffix_appears_in_format_apa(self):
        mgr = ReferenceManager()
        mgr.add(_ref(year=2020, title="B Work", source="Pub"))
        mgr.add(_ref(year=2020, title="A Work", source="Pub"))
        for ref in mgr.references:
            formatted = ref.format_apa()
            if ref.title == "A Work":
                assert "(2020a)" in formatted
            else:
                assert "(2020b)" in formatted

    def test_suffix_reset_on_remove(self):
        mgr = ReferenceManager()
        mgr.add(_ref(year=2020, title="A"))
        mgr.add(_ref(year=2020, title="B"))
        assert any(r.year_suffix is not None for r in mgr.references)
        mgr.remove(0)
        assert all(r.year_suffix is None for r in mgr.references)

    def test_group_author_disambiguation(self):
        ga = GroupAuthor(name="World Health Organization")
        mgr = ReferenceManager()
        mgr.add(_ref(authors=[ga], year=2020, title="Report A"))
        mgr.add(_ref(authors=[ga], year=2020, title="Report B"))
        suffixes = sorted(r.year_suffix for r in mgr.references)
        assert suffixes == ["a", "b"]


# ===========================================================================
# Year Suffix in Citation
# ===========================================================================


class TestCitationYearSuffix:
    def test_parenthetical_with_suffix(self):
        c = Citation(authors=["Smith"], year=2020, year_suffix="a")
        assert c.format_apa() == "(Smith, 2020a)"

    def test_narrative_with_suffix(self):
        c = Citation(
            citation_type=CitationType.NARRATIVE,
            authors=["Smith"],
            year=2020,
            year_suffix="b",
        )
        assert c.format_apa() == "Smith (2020b)"

    def test_no_suffix(self):
        c = Citation(authors=["Smith"], year=2020)
        assert c.format_apa() == "(Smith, 2020)"


# ===========================================================================
# Secondary Citations (APA 7 §8.6)
# ===========================================================================


class TestSecondaryCitation:
    """'as cited in' format for indirect sources."""

    def test_parenthetical_secondary(self):
        c = Citation(
            authors=["Freud"],
            year=1923,
            is_secondary=True,
            secondary_author="Smith",
            secondary_year=2020,
        )
        result = c.format_apa()
        assert result == "(Freud, 1923, as cited in Smith, 2020)"

    def test_narrative_secondary(self):
        c = Citation(
            citation_type=CitationType.NARRATIVE,
            authors=["Freud"],
            year=1923,
            is_secondary=True,
            secondary_author="Smith",
            secondary_year=2020,
        )
        result = c.format_apa()
        assert result == "Freud (1923, as cited in Smith, 2020)"

    def test_secondary_no_year_on_secondary(self):
        c = Citation(
            authors=["Piaget"],
            year=1952,
            is_secondary=True,
            secondary_author="Jones",
        )
        result = c.format_apa()
        assert "as cited in Jones, n.d." in result

    def test_non_secondary_unchanged(self):
        c = Citation(authors=["Smith"], year=2020, is_secondary=False)
        assert c.format_apa() == "(Smith, 2020)"


# ===========================================================================
# Personal Communications (APA 7 §8.9)
# ===========================================================================


class TestPersonalCommunication:
    """Personal communications are in-text only, never in reference list."""

    def test_basic_personal_communication(self):
        c = Citation(
            citation_type=CitationType.PERSONAL_COMMUNICATION,
            authors=["J. Smith"],
            communication_date="March 15, 2024",
        )
        result = c.format_apa()
        assert result == "(J. Smith, personal communication, March 15, 2024)"

    def test_personal_communication_no_date(self):
        c = Citation(
            citation_type=CitationType.PERSONAL_COMMUNICATION,
            authors=["A. García"],
        )
        result = c.format_apa()
        assert result == "(A. García, personal communication, n.d.)"

    def test_personal_communication_no_author(self):
        c = Citation(
            citation_type=CitationType.PERSONAL_COMMUNICATION,
            authors=[],
            communication_date="January 1, 2025",
        )
        result = c.format_apa()
        assert "Unknown" in result


# ===========================================================================
# ReferenceManager sorting
# ===========================================================================


class TestReferenceManagerSorting:
    def test_alphabetical_sort(self):
        mgr = ReferenceManager()
        mgr.references = [
            _ref(authors=[_author("Zapata", "Ana")], title="Z paper"),
            _ref(authors=[_author("Adams", "Bob")], title="A paper"),
            _ref(authors=[_author("Martinez", "Carlos")], title="M paper"),
        ]
        mgr.sort_alphabetically()
        names = [r.authors[0].last_name for r in mgr.references]
        assert names == ["Adams", "Martinez", "Zapata"]

    def test_no_author_sorted_by_title(self):
        mgr = ReferenceManager()
        mgr.references = [
            _ref(authors=[_author("Zapata", "Ana")], title="Z"),
            Reference(ref_type=ReferenceType.BOOK, title="An anonymous work", year=2020),
        ]
        mgr.sort_alphabetically()
        assert mgr.references[0].title == "An anonymous work"

    def test_format_reference_list(self):
        mgr = ReferenceManager()
        mgr.add(_ref(authors=[_author("Zapata", "Ana")], title="Z", source="Pub"))
        mgr.add(_ref(authors=[_author("Adams", "Bob")], title="A", source="Pub"))
        result = mgr.format_reference_list()
        lines = result.split("\n\n")
        assert len(lines) == 2
        assert "Adams" in lines[0]
        assert "Zapata" in lines[1]


# ===========================================================================
# Regression: existing Citation behavior
# ===========================================================================


class TestCitationRegression:
    def test_parenthetical_single(self):
        c = Citation(authors=["Smith"], year=2020)
        assert c.format_apa() == "(Smith, 2020)"

    def test_narrative_two_authors(self):
        c = Citation(
            citation_type=CitationType.NARRATIVE,
            authors=["Smith", "Jones"],
            year=2020,
        )
        assert c.format_apa() == "Smith and Jones (2020)"

    def test_three_plus_et_al(self):
        c = Citation(authors=["Smith", "Jones", "Doe"], year=2020)
        assert c.format_apa() == "(Smith et al., 2020)"

    def test_no_year(self):
        c = Citation(authors=["Smith"])
        assert c.format_apa() == "(Smith, n.d.)"

    def test_with_page(self):
        c = Citation(authors=["Smith"], year=2020, page="45")
        assert c.format_apa() == "(Smith, 2020, p. 45)"
