from __future__ import annotations

from pydantic import BaseModel, Field


class Repo(BaseModel):
    id: str
    repo: str  # owner/name on github.com
    include: list[str] = Field(
        default_factory=lambda: ["README.md", "**/README.md", "docs/**/*.md"]
    )
    exclude: list[str] = Field(
        default_factory=lambda: ["**/node_modules/**", "**/.github/**", "CHANGELOG.md"]
    )
    max_files: int = 2000
    max_bytes: int = 400_000  # skip huge generated files
    exam_domains: list[int] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class SamplesManifest(BaseModel):
    allowed_licenses: list[str] = Field(default_factory=lambda: ["MIT", "MIT-0", "Apache-2.0"])
    repos: list[Repo]
