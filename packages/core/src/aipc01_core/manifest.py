"""YAML manifest loading with pydantic validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


def load_manifest[M: BaseModel](path: Path, model: type[M]) -> M:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return model.model_validate(data)
