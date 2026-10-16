from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator


class BlogManifest(BaseModel):
    """Which posts to fetch. Relevance is decided from the URL slug before any download."""

    sitemap_index: str = "https://aws.amazon.com/sitemaps/sitemap_blogs/index/"
    blogs: list[str]  # blog path segments, e.g. machine-learning
    include: str  # regex matched against the post slug
    exclude: str = r"^$"  # regex matched against the post slug
    published_after: date = date(2024, 1, 1)
    max_posts: int | None = None
    exam_domains: list[int] = Field(default_factory=list)

    @field_validator("include", "exclude")
    @classmethod
    def _valid_regex(cls, value: str) -> str:
        re.compile(value)
        return value
