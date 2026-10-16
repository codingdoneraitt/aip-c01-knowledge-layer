"""WebVTT parsing. Auto-captions repeat each line in the next cue; we keep each line once."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TIMING_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+")
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Cue:
    start_s: float
    text: str


def parse_vtt(vtt: str) -> list[Cue]:
    cues: list[Cue] = []
    last_line = ""
    start = 0.0
    for raw in vtt.splitlines():
        timing = _TIMING_RE.match(raw)
        if timing:
            h, m, s, ms = (int(g) for g in timing.groups())
            start = h * 3600 + m * 60 + s + ms / 1000
            continue
        line = _SPACE_RE.sub(" ", _TAG_RE.sub("", raw)).strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or "-->" in line:
            continue
        if line.isdigit():  # cue identifier
            continue
        if line == last_line:
            continue
        cues.append(Cue(start, line))
        last_line = line
    return cues
