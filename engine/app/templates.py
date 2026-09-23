"""Templates are hand-written JSON files in the repo's templates/ directory."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class Template(BaseModel):
    id: str
    name: str
    description: str = ""
    multi_record: bool = False
    schema_: dict[str, Any]
    fields: dict[str, dict[str, Any]] = {}
    references: dict[str, list[Any]] = {}

    model_config = {"populate_by_name": True}

    @classmethod
    def from_file(cls, path: Path) -> "Template":
        data = json.loads(path.read_text())
        data["schema_"] = data.pop("schema")
        return cls.model_validate(data)


def load_templates(directory: Path) -> dict[str, Template]:
    templates = [Template.from_file(p) for p in sorted(directory.glob("*.json"))]
    return {t.id: t for t in templates}
