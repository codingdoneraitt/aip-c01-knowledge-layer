"""Document model shared by every fetcher."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class DocumentMeta(BaseModel):
    """Metadata written next to every document (frontmatter + Bedrock KB sidecar)."""

    source_url: str
    source_type: str  # docs | whitepaper | blog | guide | pricing | sample | talk | exam-guide
    title: str
    collection: str  # stable group id, e.g. "bedrock-userguide"
    exam_domains: list[int] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    license_note: str = ""
    fetched: date = Field(default_factory=date.today)
    extra: dict[str, str | int | float | bool] = Field(default_factory=dict)

    def kb_attributes(self) -> dict[str, Any]:
        """Flat attributes for the Bedrock Knowledge Bases `.metadata.json` sidecar.

        Bedrock accepts string, number, boolean and string-list values.
        """
        attrs: dict[str, Any] = {
            "source_url": self.source_url,
            "source_type": self.source_type,
            "title": self.title,
            "collection": self.collection,
            "fetched": self.fetched.isoformat(),
        }
        if self.exam_domains:
            attrs["exam_domains"] = [str(d) for d in self.exam_domains]
        if self.services:
            attrs["services"] = self.services
        attrs.update(self.extra)
        return attrs


class Document(BaseModel):
    meta: DocumentMeta
    body: str
    slug: str | None = None  # file name stem; derived from the source URL when omitted

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.body.strip().encode()).hexdigest()
