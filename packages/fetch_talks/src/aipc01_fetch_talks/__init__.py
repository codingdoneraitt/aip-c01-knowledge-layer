"""Fetch transcripts of official AWS event talks (YouTube captions) as timestamped markdown."""

from aipc01_fetch_talks.fetcher import TalksFetcher
from aipc01_fetch_talks.manifest import TalksManifest
from aipc01_fetch_talks.source import VideoData, VideoRef, VideoSource, YtDlpSource

__all__ = ["TalksFetcher", "TalksManifest", "VideoData", "VideoRef", "VideoSource", "YtDlpSource"]
