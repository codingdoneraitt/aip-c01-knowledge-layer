from __future__ import annotations

import re

from aipc01_fetch_docs.manifest import Guide
from pydantic import BaseModel, Field, field_validator


class Solutions(BaseModel):
    """Solutions Library pages, discovered through the public solutions sitemap."""

    sitemap: str = "https://aws.amazon.com/sitemaps/sitemap_solutions/"
    path_prefixes: list[str] = Field(default_factory=lambda: ["/solutions/guidance/"])
    include: str = ".*"  # regex on the page slug
    exam_domains: list[int] = Field(default_factory=list)

    @field_validator("include")
    @classmethod
    def _valid_regex(cls, value: str) -> str:
        re.compile(value)
        return value


class GuidesManifest(BaseModel):
    docs_guides: list[Guide] = Field(default_factory=list)
    solutions: Solutions | None = None
