from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from datetime import datetime

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.http import FetchError
from aipc01_core.report import Failure

from aipc01_fetch_talks.manifest import Channel, TalksManifest
from aipc01_fetch_talks.source import VideoSource, YtDlpSource
from aipc01_fetch_talks.transcript import to_markdown
from aipc01_fetch_talks.vtt import parse_vtt

log = logging.getLogger(__name__)


class TalksFetcher(BaseFetcher):
    """Does not use the HTTP client: yt-dlp talks to YouTube. Run with few workers."""

    source = "talks"

    def __init__(
        self, manifest: TalksManifest, *args, video_source: VideoSource | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.manifest = manifest
        self.videos = video_source or YtDlpSource()

    def discover(self) -> Iterable[Target]:
        for channel in self.manifest.channels:
            try:
                refs = self.videos.list_videos(channel.videos_url, channel.scan_limit)
            except RuntimeError as exc:
                self.discovery_failures.append(Failure(channel.videos_url, str(exc)))
                continue
            include, exclude = re.compile(channel.include, re.I), re.compile(channel.exclude, re.I)
            chosen = [
                r
                for r in refs
                if include.search(r.title)
                and not exclude.search(r.title)
                and channel.min_duration_s <= r.duration_s <= channel.max_duration_s
            ][: channel.max_videos]
            log.info("%s: %d of %d videos match", channel.id, len(chosen), len(refs))
            for ref in chosen:
                yield Target(
                    f"https://www.youtube.com/watch?v={ref.id}", {"channel": channel, "ref": ref}
                )

    def fetch(self, target: Target) -> list[Document]:
        channel: Channel = target.context["channel"]  # type: ignore[assignment]
        ref = target.context["ref"]
        try:
            video = self.videos.fetch(ref.id)  # type: ignore[attr-defined]
        except RuntimeError as exc:
            raise FetchError(str(exc)) from exc
        if video.channel_id != channel.channel_id:
            raise FetchError(f"video belongs to channel {video.channel_id}, not the official one")
        uploaded = (
            datetime.strptime(video.upload_date, "%Y%m%d").date() if video.upload_date else None
        )
        if video.vtt is None or uploaded is None or uploaded < channel.uploaded_after:
            return []
        cues = parse_vtt(video.vtt)
        meta = DocumentMeta(
            source_url=target.url,
            source_type="talk",
            title=video.title,
            collection=channel.id,
            exam_domains=channel.exam_domains,
            license_note=f"Official {channel.name} channel; captions kept local.",
            extra={
                "video_id": video.id,
                "channel": video.channel,
                "uploaded": uploaded.isoformat(),
                "duration_s": video.duration_s,
            },
        )
        return [
            Document(meta=meta, body=to_markdown(video, cues), slug=f"{uploaded:%Y-%m}--{video.id}")
        ]
