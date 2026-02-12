"""Project persistence — save/load reference collections as JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from apa_formatter.models.document import Reference


# Default storage directory
_DEFAULT_DIR = Path.home() / ".apa_formatter" / "projects"


class Project(BaseModel):
    """A serialisable collection of APA references.

    Attributes:
        title: Human-readable project name.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-modified timestamp.
        references: The reference list.
    """

    title: str = "Untitled Project"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    references: list[Reference] = Field(default_factory=list)

    # -- Serialisation -------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return dict(json.loads(self.model_dump_json()))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        """Create a Project from a dictionary (e.g. parsed JSON)."""
        return cls.model_validate(data)

    # -- Convenience ---------------------------------------------------------

    def touch(self) -> None:
        """Update ``updated_at`` to *now*."""
        self.updated_at = datetime.now(timezone.utc).isoformat()


# -- File I/O ----------------------------------------------------------------


def save_project(project: Project, path: str | Path | None = None) -> Path:
    """Persist a project to a JSON file.

    Args:
        project: The project to save.
        path: Destination file path.  If *None*, saves to
              ``~/.apa_formatter/projects/<title>.json``.

    Returns:
        The resolved ``Path`` that was written.
    """
    project.touch()

    if path is None:
        _DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = project.title.replace(" ", "_").lower()
        path = _DEFAULT_DIR / f"{safe_name}.json"
    else:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def load_project(path: str | Path) -> Project:
    """Load a project from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        A reconstituted ``Project``.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the JSON cannot be parsed into a ``Project``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Project file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Project.from_dict(data)
    except (json.JSONDecodeError, Exception) as exc:
        raise ValueError(f"Failed to load project from {path}: {exc}") from exc


def list_projects(directory: str | Path | None = None) -> list[Path]:
    """Return all ``.json`` project files in *directory*.

    Args:
        directory: Defaults to ``~/.apa_formatter/projects/``.
    """
    d = Path(directory) if directory else _DEFAULT_DIR
    if not d.exists():
        return []
    return sorted(d.glob("*.json"))
