"""Turns caption cues into readable markdown paragraphs with deep links to the video."""

from __future__ import annotations

from aipc01_fetch_talks.source import VideoData
from aipc01_fetch_talks.vtt import Cue

PARAGRAPH_SECONDS = 60


def timestamp(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def _paragraphs(cues: list[Cue], video_id: str) -> list[str]:
    out: list[str] = []
    window_start, words = None, []
    for cue in cues:
        if window_start is None:
            window_start = cue.start_s
        elif cue.start_s - window_start >= PARAGRAPH_SECONDS:
            out.append(_render(video_id, window_start, words))
            window_start, words = cue.start_s, []
        words.append(cue.text)
    if words and window_start is not None:
        out.append(_render(video_id, window_start, words))
    return out


def _render(video_id: str, start: float, words: list[str]) -> str:
    link = f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"
    return f"**[{timestamp(start)}]({link})** {' '.join(words)}"


def to_markdown(video: VideoData, cues: list[Cue]) -> str:
    header = [
        f"# {video.title}",
        f"Source: [{video.channel}](https://www.youtube.com/channel/{video.channel_id}), "
        f"[watch](https://www.youtube.com/watch?v={video.id}), "
        f"{timestamp(video.duration_s)} long, uploaded {video.upload_date}. Auto captions.",
    ]
    return "\n\n".join([*header, "## Transcript", *_paragraphs(cues, video.id)])
