"""Tests for all APA 7 reference format types.

Covers the 9 newly implemented formats (conference, dissertation, report,
newspaper, magazine, software, audiovisual, social media, legal) plus
GroupAuthor and the no-author edge case.
"""

from datetime import date


from apa_formatter.models.document import (
    Author,
    GroupAuthor,
    Reference,
)
from apa_formatter.models.enums import ReferenceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _author(last="Smith", first="John", mid=None):
    return Author(last_name=last, first_name=first, middle_initial=mid)


# ---------------------------------------------------------------------------
# GroupAuthor
# ---------------------------------------------------------------------------


class TestGroupAuthor:
    def test_apa_format_returns_name_unchanged(self):
        ga = GroupAuthor(name="World Health Organization")
        assert ga.apa_format == "World Health Organization"

    def test_abbreviation_stored(self):
        ga = GroupAuthor(name="American Psychological Association", abbreviation="APA")
        assert ga.abbreviation == "APA"
        assert ga.apa_format == "American Psychological Association"

    def test_apa_narrative(self):
        ga = GroupAuthor(name="UNESCO")
        assert ga.apa_narrative == "UNESCO"

    def test_group_author_in_reference(self):
        ref = Reference(
            ref_type=ReferenceType.REPORT,
            authors=[GroupAuthor(name="World Health Organization")],
            year=2020,
            title="COVID-19 Situation Report",
            report_number="51",
            url="https://www.who.int/report",
        )
        result = ref.format_apa()
        assert "World Health Organization" in result
        assert "(2020)" in result
        assert "(Report No. 51)" in result


# ---------------------------------------------------------------------------
# Conference Paper
# ---------------------------------------------------------------------------


class TestConferencePaper:
    def test_basic_conference(self):
        ref = Reference(
            ref_type=ReferenceType.CONFERENCE_PAPER,
            authors=[_author("Pérez", "Ana")],
            year=2023,
            title="Machine Learning in Education",
            source="International Conference on AI",
            conference_location="Barcelona, Spain",
        )
        result = ref.format_apa()
        assert "Pérez, A." in result
        assert "(2023)" in result
        assert "*Machine Learning in Education*" in result
        assert "[Conference presentation]" in result
        assert "Barcelona, Spain" in result

    def test_conference_with_custom_media_type(self):
        ref = Reference(
            ref_type=ReferenceType.CONFERENCE_PAPER,
            authors=[_author()],
            year=2022,
            title="Some Poster",
            source="ACM Conference",
            media_type="Poster session",
        )
        result = ref.format_apa()
        assert "[Poster session]" in result

    def test_conference_with_doi(self):
        ref = Reference(
            ref_type=ReferenceType.CONFERENCE_PAPER,
            authors=[_author()],
            year=2021,
            title="Paper Title",
            source="Conference",
            doi="10.1234/conf.2021",
        )
        result = ref.format_apa()
        assert "https://doi.org/10.1234/conf.2021" in result


# ---------------------------------------------------------------------------
# Dissertation
# ---------------------------------------------------------------------------


class TestDissertation:
    def test_basic_dissertation(self):
        ref = Reference(
            ref_type=ReferenceType.DISSERTATION,
            authors=[_author("García", "María", "L")],
            year=2019,
            title="Neural Network Applications",
            university="Universidad Nacional",
            source="ProQuest Dissertations",
            url="https://proquest.com/123",
        )
        result = ref.format_apa()
        assert "García, M. L." in result
        assert "(2019)" in result
        assert "*Neural Network Applications*" in result
        assert "[Doctoral dissertation, Universidad Nacional]" in result
        assert "ProQuest Dissertations." in result
        assert "https://proquest.com/123" in result

    def test_masters_thesis(self):
        ref = Reference(
            ref_type=ReferenceType.DISSERTATION,
            authors=[_author()],
            year=2020,
            title="My Thesis",
            university="MIT",
            media_type="Master's thesis",
        )
        result = ref.format_apa()
        assert "[Master's thesis, MIT]" in result

    def test_dissertation_no_university(self):
        ref = Reference(
            ref_type=ReferenceType.DISSERTATION,
            authors=[_author()],
            year=2018,
            title="A Study",
        )
        result = ref.format_apa()
        assert "[Doctoral dissertation]" in result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


class TestReport:
    def test_report_with_number(self):
        ref = Reference(
            ref_type=ReferenceType.REPORT,
            authors=[_author("López", "Carlos")],
            year=2021,
            title="Economic Impact Analysis",
            report_number="2021-45",
            source="Ministry of Finance",
            url="https://gov.co/report",
        )
        result = ref.format_apa()
        assert "López, C." in result
        assert "(Report No. 2021-45)" in result
        assert "Ministry of Finance." in result

    def test_report_without_number(self):
        ref = Reference(
            ref_type=ReferenceType.REPORT,
            authors=[_author()],
            year=2022,
            title="Annual Report",
            source="Publisher",
        )
        result = ref.format_apa()
        assert "*Annual Report*." in result
        assert "(Report No." not in result


# ---------------------------------------------------------------------------
# Newspaper
# ---------------------------------------------------------------------------


class TestNewspaper:
    def test_newspaper_article(self):
        ref = Reference(
            ref_type=ReferenceType.NEWSPAPER,
            authors=[_author("Rodríguez", "Elena")],
            year=2024,
            title="Inflation Hits Record High",
            source="El Tiempo",
            pages="A1, A4",
            url="https://eltiempo.com/article",
        )
        result = ref.format_apa()
        assert "Rodríguez, E." in result
        assert "Inflation Hits Record High." in result
        assert "*El Tiempo*" in result
        assert "A1, A4" in result
        assert "https://eltiempo.com/article" in result

    def test_newspaper_no_pages(self):
        ref = Reference(
            ref_type=ReferenceType.NEWSPAPER,
            authors=[_author()],
            year=2023,
            title="Article Title",
            source="New York Times",
        )
        result = ref.format_apa()
        assert "*New York Times*." in result


# ---------------------------------------------------------------------------
# Magazine
# ---------------------------------------------------------------------------


class TestMagazine:
    def test_magazine_with_volume_issue(self):
        ref = Reference(
            ref_type=ReferenceType.MAGAZINE,
            authors=[_author("Adams", "Rebecca")],
            year=2023,
            title="The Future of Work",
            source="Time",
            volume="201",
            issue="5",
            pages="34-40",
        )
        result = ref.format_apa()
        assert "Adams, R." in result
        assert "*Time*" in result
        assert "*201*" in result
        assert "(5)" in result
        assert "34-40" in result

    def test_magazine_minimal(self):
        ref = Reference(
            ref_type=ReferenceType.MAGAZINE,
            authors=[_author()],
            year=2022,
            title="Short Piece",
            source="Wired",
        )
        result = ref.format_apa()
        assert "*Wired*." in result


# ---------------------------------------------------------------------------
# Software
# ---------------------------------------------------------------------------


class TestSoftware:
    def test_software_with_version(self):
        ref = Reference(
            ref_type=ReferenceType.SOFTWARE,
            authors=[_author("van Rossum", "Guido")],
            year=2023,
            title="Python",
            edition="3.12",
            url="https://python.org",
        )
        result = ref.format_apa()
        assert "van Rossum, G." in result
        assert "*Python*" in result
        assert "(Version 3.12)" in result
        assert "[Computer software]" in result
        assert "https://python.org" in result

    def test_software_custom_media_type(self):
        ref = Reference(
            ref_type=ReferenceType.SOFTWARE,
            authors=[_author()],
            year=2024,
            title="MyApp",
            media_type="Mobile app",
        )
        result = ref.format_apa()
        assert "[Mobile app]" in result


# ---------------------------------------------------------------------------
# Audiovisual
# ---------------------------------------------------------------------------


class TestAudiovisual:
    def test_film(self):
        ref = Reference(
            ref_type=ReferenceType.AUDIOVISUAL,
            authors=[_author("Nolan", "Christopher")],
            year=2023,
            title="Oppenheimer",
            source="Universal Pictures",
            media_type="Film",
        )
        result = ref.format_apa()
        assert "Nolan, C." in result
        assert "*Oppenheimer*" in result
        assert "[Film]" in result
        assert "Universal Pictures." in result

    def test_podcast(self):
        ref = Reference(
            ref_type=ReferenceType.AUDIOVISUAL,
            authors=[_author("Gladwell", "Malcolm")],
            year=2021,
            title="Revisionist History",
            source="Pushkin Industries",
            media_type="Podcast",
        )
        result = ref.format_apa()
        assert "[Podcast]" in result

    def test_audiovisual_default_media(self):
        ref = Reference(
            ref_type=ReferenceType.AUDIOVISUAL,
            authors=[_author()],
            year=2020,
            title="Something",
        )
        result = ref.format_apa()
        assert "[Film]" in result


# ---------------------------------------------------------------------------
# Social Media
# ---------------------------------------------------------------------------


class TestSocialMedia:
    def test_tweet_with_username(self):
        ref = Reference(
            ref_type=ReferenceType.SOCIAL_MEDIA,
            authors=[_author("Biden", "Joseph", "R")],
            year=2024,
            title="Today we announced new infrastructure investments",
            username="@POTUS",
            media_type="Tweet",
            platform="Twitter",
            url="https://twitter.com/POTUS/status/123",
        )
        result = ref.format_apa()
        assert "Biden, J. R." in result
        assert "[@POTUS]" in result
        assert "[Tweet]" in result
        assert "Twitter." in result
        assert "https://twitter.com/POTUS/status/123" in result

    def test_social_media_username_only(self):
        ref = Reference(
            ref_type=ReferenceType.SOCIAL_MEDIA,
            username="@NASA",
            year=2023,
            title="Artemis II crew announced",
            platform="Instagram",
            media_type="Post",
            url="https://instagram.com/p/123",
        )
        result = ref.format_apa()
        assert "@NASA." in result
        assert "[Post]" in result
        assert "Instagram." in result

    def test_social_media_no_author_no_username(self):
        ref = Reference(
            ref_type=ReferenceType.SOCIAL_MEDIA,
            year=2023,
            title="Anonymous post content",
            platform="Reddit",
        )
        result = ref.format_apa()
        assert "(2023)" in result
        assert "Anonymous post content" in result
        assert "Reddit." in result


# ---------------------------------------------------------------------------
# Legal
# ---------------------------------------------------------------------------


class TestLegal:
    def test_basic_law(self):
        ref = Reference(
            ref_type=ReferenceType.LEGAL,
            year=1994,
            title="Ley General de Educación",
            source="Congreso de Colombia",
            volume="115",
        )
        result = ref.format_apa()
        assert "Ley General de Educación," in result
        assert "Congreso de Colombia" in result
        assert "§ 115" in result
        assert "(1994)" in result

    def test_legal_no_year(self):
        ref = Reference(
            ref_type=ReferenceType.LEGAL,
            title="Some Regulation",
            source="Federal Register",
        )
        result = ref.format_apa()
        assert "(n.d.)" in result

    def test_legal_with_url(self):
        ref = Reference(
            ref_type=ReferenceType.LEGAL,
            year=2020,
            title="GDPR",
            source="EU Official Journal",
            url="https://eur-lex.europa.eu/gdpr",
        )
        result = ref.format_apa()
        assert "https://eur-lex.europa.eu/gdpr" in result


# ---------------------------------------------------------------------------
# No Author Edge Case
# ---------------------------------------------------------------------------


class TestNoAuthor:
    def test_no_author_journal(self):
        """No-author reference starts with year (title stays in title position)."""
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            year=2023,
            title="Untitled Study",
            source="Journal X",
        )
        result = ref.format_apa()
        assert result.startswith("(2023).")

    def test_no_author_webpage(self):
        ref = Reference(
            ref_type=ReferenceType.WEBPAGE,
            year=2024,
            title="Government Data Portal",
            source="Data.gov",
            url="https://data.gov",
        )
        result = ref.format_apa()
        assert "(2024)" in result
        assert "*Government Data Portal*" in result

    def test_no_author_no_date(self):
        ref = Reference(
            ref_type=ReferenceType.BOOK,
            title="Anonymous Work",
            source="Publisher",
        )
        result = ref.format_apa()
        assert "(n.d.)" in result
        assert "*Anonymous Work*" in result


# ---------------------------------------------------------------------------
# Existing formats still work (regression)
# ---------------------------------------------------------------------------


class TestRegressionExistingFormats:
    """Ensure the refactored code produces identical output for previously
    working reference types."""

    def test_journal_article_with_doi(self):
        ref = Reference(
            ref_type=ReferenceType.JOURNAL_ARTICLE,
            authors=[_author()],
            year=2023,
            title="Test Article",
            source="Test Journal",
            volume="15",
            issue="3",
            pages="234-256",
            doi="10.1234/test",
        )
        result = ref.format_apa()
        assert "https://doi.org/10.1234/test" in result
        assert "*Test Journal*" in result
        assert "*15*" in result

    def test_book_with_edition(self):
        ref = Reference(
            ref_type=ReferenceType.BOOK,
            authors=[_author()],
            year=2020,
            title="Test Book",
            source="Publisher",
            edition="3",
        )
        result = ref.format_apa()
        assert "*Test Book*" in result
        assert "(3 ed.)" in result

    def test_webpage_basic(self):
        ref = Reference(
            ref_type=ReferenceType.WEBPAGE,
            authors=[_author()],
            year=2024,
            title="Test Page",
            source="Example.com",
            url="https://example.com",
        )
        result = ref.format_apa()
        assert "https://example.com" in result
        assert "Example.com" in result

    def test_book_chapter(self):
        ref = Reference(
            ref_type=ReferenceType.BOOK_CHAPTER,
            authors=[_author("Doe", "Jane")],
            year=2021,
            title="Chapter Title",
            source="Book Title",
            editors=[_author("Editor", "Ed")],
            pages="100-120",
        )
        result = ref.format_apa()
        assert "Doe, J." in result
        assert "In Editor, E. (Eds.)," in result
        assert "*Book Title*" in result
        assert "(pp. 100-120)" in result

    def test_webpage_with_retrieval_date(self):
        ref = Reference(
            ref_type=ReferenceType.WEBPAGE,
            authors=[_author()],
            year=2024,
            title="Dynamic Page",
            source="Wiki.com",
            url="https://wiki.com/page",
            retrieval_date=date(2024, 6, 15),
        )
        result = ref.format_apa()
        assert "Retrieved June 15, 2024, from" in result
        assert "https://wiki.com/page" in result
