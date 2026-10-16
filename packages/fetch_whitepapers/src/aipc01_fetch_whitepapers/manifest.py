from __future__ import annotations

from pydantic import BaseModel, Field


class Whitepaper(BaseModel):
    id: str
    title: str
    url: str  # direct PDF link
    exam_domains: list[int] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class WhitepaperManifest(BaseModel):
    whitepapers: list[Whitepaper]
