"""JSON repository — implements ReferenceRepositoryPort using JSON files.

Wraps the existing persistence.py logic.
"""

from __future__ import annotations

import json
from pathlib import Path

from apa_formatter.domain.models.reference import Reference
from apa_formatter.domain.ports.reference_repository import ReferenceRepositoryPort


class JsonReferenceRepository(ReferenceRepositoryPort):
    """Persist references as JSON files via the existing persistence module."""

    def save(self, references: list[Reference], path: Path) -> None:
        """Serialize references to JSON and write to *path*."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [json.loads(ref.model_dump_json()) for ref in references]
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self, path: Path) -> list[Reference]:
        """Load references from a JSON file at *path*."""
        if not path.exists():
            raise FileNotFoundError(f"Reference file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [Reference.model_validate(item) for item in data]
        # Support the Project dict format (has 'references' key)
        if isinstance(data, dict) and "references" in data:
            return [Reference.model_validate(item) for item in data["references"]]
        raise ValueError(f"Unexpected JSON format in {path}")
