"""Writes documents as markdown with YAML frontmatter plus a Bedrock KB metadata sidecar."""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

import yaml

from aipc01_core.models import Document

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class WriteResult(Enum):
    WRITTEN = "written"
    UNCHANGED = "unchanged"


def slugify(text: str, max_len: int = 120) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "untitled"


def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    tail = parsed.path.strip("/")
    for suffix in (".html", ".md", ".pdf"):
        tail = tail.removesuffix(suffix)
    return slugify(f"{parsed.netloc}-{tail}" if not tail else tail.replace("/", "-"))


class DocumentStore:
    """Layout: <root>/<source_type>/<collection>/<slug>.md (+ .md.metadata.json)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, doc: Document, slug: str) -> Path:
        return self.root / doc.meta.source_type / doc.meta.collection / f"{slug}.md"

    def write(self, doc: Document) -> tuple[Path, WriteResult]:
        slug = doc.slug or slug_from_url(doc.meta.source_url)
        path = self.path_for(doc, slug)
        rendered = self._render(doc)
        if path.exists() and self._same_content(path, doc):
            return path, WriteResult.UNCHANGED
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        sidecar = path.with_name(path.name + ".metadata.json")
        sidecar.write_text(
            json.dumps({"metadataAttributes": doc.meta.kb_attributes()}, indent=2),
            encoding="utf-8",
        )
        return path, WriteResult.WRITTEN

    @staticmethod
    def _render(doc: Document) -> str:
        front = doc.meta.model_dump(mode="json", exclude_defaults=False)
        front["content_hash"] = doc.content_hash
        header = yaml.safe_dump(front, sort_keys=False, allow_unicode=True).strip()
        return f"---\n{header}\n---\n\n{doc.body.strip()}\n"

    @staticmethod
    def _same_content(path: Path, doc: Document) -> bool:
        head = path.read_text(encoding="utf-8").split("\n---\n", 1)[0]
        return f"content_hash: {doc.content_hash}" in head
