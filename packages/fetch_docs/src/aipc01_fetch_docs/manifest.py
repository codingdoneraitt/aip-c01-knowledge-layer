from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Guide(BaseModel):
    """One docs.aws.amazon.com guide, crawled through its sitemap."""

    id: str
    title: str
    base_url: str  # e.g. https://docs.aws.amazon.com/bedrock/latest/userguide
    source_type: str = "docs"  # docs | whitepaper | guide
    exam_domains: list[int] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)

    @field_validator("base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def sitemap_url(self) -> str:
        return f"{self.base_url}/sitemap.xml"


class LlmsSite(BaseModel):
    """A documentation site that publishes an `llms.txt` index of markdown pages."""

    id: str
    title: str
    llms_url: str
    source_type: str = "docs"
    include: str = ".*"  # regex on the page URL
    exclude: str = r"^$"
    exam_domains: list[int] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class DocsManifest(BaseModel):
    guides: list[Guide] = Field(default_factory=list)
    llms_sites: list[LlmsSite] = Field(default_factory=list)
