from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator


class Channel(BaseModel):
    """An official channel. `channel_id` is checked on every video, so look-alikes are rejected."""

    id: str
    name: str
    channel_id: str  # YouTube UC... id
    videos_url: str
    include: str  # regex on the video title
    exclude: str = r"^$"
    min_duration_s: int = 600
    max_duration_s: int = 6 * 3600
    uploaded_after: date = date(2025, 1, 1)
    scan_limit: int = 1500  # how many channel entries to inspect
    max_videos: int = 150
    exam_domains: list[int] = Field(default_factory=list)

    @field_validator("include", "exclude")
    @classmethod
    def _valid_regex(cls, value: str) -> str:
        re.compile(value)
        return value


class TalksManifest(BaseModel):
    channels: list[Channel]
