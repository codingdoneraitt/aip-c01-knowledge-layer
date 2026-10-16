"""Access to YouTube metadata and captions, behind a Protocol so tests need no network."""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class VideoRef:
    id: str
    title: str
    duration_s: int


@dataclass(frozen=True)
class VideoData:
    id: str
    title: str
    channel_id: str
    channel: str
    upload_date: str  # YYYYMMDD
    duration_s: int
    description: str
    chapters: list[dict] = field(default_factory=list)
    vtt: str | None = None  # English captions, None when the video has none


class VideoSource(Protocol):
    def list_videos(self, videos_url: str, limit: int) -> list[VideoRef]: ...

    def fetch(self, video_id: str) -> VideoData: ...


class YtDlpSource:
    RATE_LIMIT_BACKOFF_S = (30, 90, 180)

    def __init__(
        self,
        sleep_s: int = 2,
        binary: str = "yt-dlp",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.sleep_s = sleep_s
        self.binary = binary
        self._sleep = sleep

    def list_videos(self, videos_url: str, limit: int) -> list[VideoRef]:
        out = self._run("--flat-playlist", "--playlist-end", str(limit), "-J", videos_url)
        return [
            VideoRef(e["id"], e.get("title") or "", int(e.get("duration") or 0))
            for e in json.loads(out)["entries"]
            if e.get("id")
        ]

    def fetch(self, video_id: str) -> VideoData:
        with tempfile.TemporaryDirectory() as tmp:
            self._run(
                "--skip-download",
                "--write-info-json",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                "en.*,en",
                "--sub-format",
                "vtt",
                "--sleep-subtitles",
                str(self.sleep_s),
                "-o",
                f"{tmp}/v",
                f"https://www.youtube.com/watch?v={video_id}",
            )
            info = json.loads((Path(tmp) / "v.info.json").read_text())
            vtts = sorted(Path(tmp).glob("v.*.vtt"), key=lambda p: ("orig" not in p.name, p.name))
            return VideoData(
                id=video_id,
                title=info.get("title") or "",
                channel_id=info.get("channel_id") or "",
                channel=info.get("channel") or "",
                upload_date=info.get("upload_date") or "",
                duration_s=int(info.get("duration") or 0),
                description=info.get("description") or "",
                chapters=info.get("chapters") or [],
                vtt=vtts[0].read_text(encoding="utf-8") if vtts else None,
            )

    def _run(self, *args: str) -> str:
        """Run yt-dlp, backing off and retrying when YouTube answers HTTP 429."""
        for delay in (*self.RATE_LIMIT_BACKOFF_S, None):
            proc = subprocess.run(
                [self.binary, "--no-warnings", "--sleep-requests", "1", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                return proc.stdout
            if "429" not in proc.stderr or delay is None:
                break
            self._sleep(delay)
        raise RuntimeError(f"yt-dlp failed: {proc.stderr.strip()[-300:]}")
