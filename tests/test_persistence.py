"""Tests for session persistence and clipboard — Sprint 5."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apa_formatter.clipboard import (
    ClipboardError,
    copy_reference,
    copy_to_clipboard,
)
from apa_formatter.models.document import Author, Reference
from apa_formatter.models.enums import ReferenceType
from apa_formatter.persistence import (
    Project,
    list_projects,
    load_project,
    save_project,
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

_SMITH = Author(first_name="John", last_name="Smith")


def _ref(**overrides) -> Reference:
    defaults = dict(
        title="Test Book",
        ref_type=ReferenceType.BOOK,
        authors=[_SMITH],
        year=2023,
        source="Pub Co.",
    )
    defaults.update(overrides)
    return Reference(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# Project Model
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectModel:
    """Tests for the Project Pydantic model."""

    def test_default_title(self):
        p = Project()
        assert p.title == "Untitled Project"

    def test_custom_title(self):
        p = Project(title="My Thesis")
        assert p.title == "My Thesis"

    def test_created_at_auto_set(self):
        p = Project()
        assert p.created_at  # Should be a non-empty ISO string

    def test_references_default_empty(self):
        p = Project()
        assert p.references == []

    def test_add_references(self):
        p = Project(references=[_ref(), _ref(title="Another")])
        assert len(p.references) == 2

    def test_to_dict_is_serialisable(self):
        p = Project(title="Test", references=[_ref()])
        d = p.to_dict()
        # Must be JSON-serialisable
        json_str = json.dumps(d)
        assert '"title": "Test"' in json_str

    def test_from_dict_roundtrip(self):
        p = Project(title="RT", references=[_ref()])
        d = p.to_dict()
        p2 = Project.from_dict(d)
        assert p2.title == "RT"
        assert len(p2.references) == 1
        assert p2.references[0].title == "Test Book"

    def test_touch_updates_timestamp(self):
        p = Project()
        old = p.updated_at
        # Ensure different timestamp
        import time

        time.sleep(0.01)
        p.touch()
        assert p.updated_at != old


# ═══════════════════════════════════════════════════════════════════════════════
# Save / Load
# ═══════════════════════════════════════════════════════════════════════════════


class TestSaveLoad:
    """Tests for save_project / load_project."""

    def test_save_and_load(self, tmp_path: Path):
        p = Project(title="Saved", references=[_ref()])
        dest = tmp_path / "test.json"
        result = save_project(p, dest)
        assert result == dest
        assert dest.exists()

        loaded = load_project(dest)
        assert loaded.title == "Saved"
        assert len(loaded.references) == 1

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        dest = tmp_path / "sub" / "deep" / "project.json"
        save_project(Project(), dest)
        assert dest.exists()

    def test_save_default_path(self, tmp_path: Path, monkeypatch):
        """When no path is given, uses ~/.apa_formatter/projects/<title>.json."""
        monkeypatch.setattr(
            "apa_formatter.persistence._DEFAULT_DIR",
            tmp_path,
        )
        p = Project(title="My Project")
        result = save_project(p)
        assert result == tmp_path / "my_project.json"
        assert result.exists()

    def test_load_nonexistent(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_project(tmp_path / "nonexistent.json")

    def test_load_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all", encoding="utf-8")
        with pytest.raises(ValueError, match="Failed to load"):
            load_project(bad)

    def test_round_trip_multiple_references(self, tmp_path: Path):
        refs = [_ref(title=f"Book {i}") for i in range(5)]
        p = Project(title="Multi", references=refs)
        dest = tmp_path / "multi.json"
        save_project(p, dest)
        loaded = load_project(dest)
        assert len(loaded.references) == 5
        assert [r.title for r in loaded.references] == [f"Book {i}" for i in range(5)]


# ═══════════════════════════════════════════════════════════════════════════════
# List Projects
# ═══════════════════════════════════════════════════════════════════════════════


class TestListProjects:
    """Tests for list_projects()."""

    def test_empty_directory(self, tmp_path: Path):
        assert list_projects(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path: Path):
        assert list_projects(tmp_path / "nope") == []

    def test_lists_json_files(self, tmp_path: Path):
        (tmp_path / "a.json").write_text("{}")
        (tmp_path / "b.json").write_text("{}")
        (tmp_path / "c.txt").write_text("not json")
        result = list_projects(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".json" for p in result)


# ═══════════════════════════════════════════════════════════════════════════════
# Clipboard
# ═══════════════════════════════════════════════════════════════════════════════


class TestClipboard:
    """Tests for clipboard operations (mocked — no real clipboard needed)."""

    @patch("apa_formatter.clipboard._detect_backend", return_value=["pbcopy"])
    @patch("apa_formatter.clipboard.subprocess.run")
    def test_copy_to_clipboard(self, mock_run: MagicMock, mock_detect: MagicMock):
        copy_to_clipboard("Hello APA")
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["input"] == b"Hello APA"

    @patch("apa_formatter.clipboard._detect_backend", return_value=["pbcopy"])
    @patch("apa_formatter.clipboard.subprocess.run")
    def test_copy_reference(self, mock_run: MagicMock, mock_detect: MagicMock):
        ref = _ref()
        result = copy_reference(ref)
        assert "Smith, J." in result  # Author format
        assert "(2023)" in result
        mock_run.assert_called_once()

    @patch("apa_formatter.clipboard._detect_backend", return_value=["pbcopy"])
    @patch("apa_formatter.clipboard.subprocess.run")
    def test_copy_reference_with_locale(self, mock_run: MagicMock, mock_detect: MagicMock):
        from apa_formatter.locale import get_locale

        ref = _ref(year=None)
        result = copy_reference(ref, locale=get_locale("es"))
        assert "(s.f.)" in result

    @patch(
        "apa_formatter.clipboard._detect_backend",
        side_effect=ClipboardError("No tool"),
    )
    def test_copy_fails_no_backend(self, mock_detect: MagicMock):
        with pytest.raises(ClipboardError, match="No tool"):
            copy_to_clipboard("test")

    @patch("apa_formatter.clipboard._detect_backend", return_value=["pbcopy"])
    @patch(
        "apa_formatter.clipboard.subprocess.run",
        side_effect=__import__("subprocess").CalledProcessError(1, "pbcopy"),
    )
    def test_copy_fails_subprocess_error(self, mock_run: MagicMock, mock_detect: MagicMock):
        with pytest.raises(ClipboardError, match="Clipboard copy failed"):
            copy_to_clipboard("test")
