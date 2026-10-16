import httpx
import pytest
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_talks import TalksFetcher, TalksManifest, VideoData, VideoRef
from aipc01_fetch_talks.transcript import timestamp
from aipc01_fetch_talks.vtt import parse_vtt

ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:03.000 align:start position:0%
welcome to<00:00:01.000><c> this</c><00:00:02.000><c> session</c>

00:00:03.000 --> 00:00:05.000 align:start position:0%
welcome to this session
today we cover<00:00:04.000><c> RAG</c>

00:01:10.000 --> 00:01:12.000
today we cover RAG
with Bedrock Knowledge Bases
"""
OFFICIAL = "UCdoadna9HFHsxXWhafhNvKw"


def video(video_id="v1", channel_id=OFFICIAL, upload="20260301", vtt=ROLLING_VTT):
    return VideoData(
        id=video_id,
        title=f"Talk {video_id}",
        channel_id=channel_id,
        channel="AWS Events",
        upload_date=upload,
        duration_s=1800,
        description="",
        vtt=vtt,
    )


class FakeSource:
    def __init__(self, refs, videos):
        self.refs, self.videos = refs, videos

    def list_videos(self, videos_url, limit):
        return self.refs[:limit]

    def fetch(self, video_id):
        return self.videos[video_id]


MANIFEST = TalksManifest.model_validate(
    {
        "channels": [
            {
                "id": "aws-events",
                "name": "AWS Events",
                "channel_id": OFFICIAL,
                "videos_url": "https://www.youtube.com/@AWSEventsChannel/videos",
                "include": r"bedrock|rag",
                "exclude": r"keynote",
                "exam_domains": [1],
            }
        ]
    }
)


def fetcher(tmp_path, refs, videos):
    client = PoliteClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    return TalksFetcher(
        MANIFEST, client, DocumentStore(tmp_path), video_source=FakeSource(refs, videos)
    )


def test_parse_vtt_dedupes_rolling_captions_and_strips_tags():
    cues = parse_vtt(ROLLING_VTT)
    assert [c.text for c in cues] == [
        "welcome to this session",
        "today we cover RAG",
        "with Bedrock Knowledge Bases",
    ]
    assert cues[1].start_s == 3.0 and cues[2].start_s == 70.0


def test_timestamp_formatting():
    assert timestamp(75) == "1:15" and timestamp(3725) == "1:02:05"


def test_discovery_filters_on_title_duration_and_exclusions(tmp_path):
    refs = [
        VideoRef("a", "Bedrock deep dive", 1800),
        VideoRef("b", "Bedrock keynote", 1800),
        VideoRef("c", "Bedrock teaser", 60),
        VideoRef("d", "Unrelated", 1800),
    ]
    assert [t.url.rsplit("=", 1)[1] for t in fetcher(tmp_path, refs, {}).discover()] == ["a"]


def test_transcript_document_has_timestamp_links(tmp_path):
    f = fetcher(tmp_path, [VideoRef("v1", "Bedrock RAG", 1800)], {"v1": video()})
    report = f.run()
    assert (report.written, report.failed, report.invalid) == (1, [], [])
    text = (tmp_path / "talk/aws-events/2026-03--v1.md").read_text()
    assert (
        "**[0:00](https://www.youtube.com/watch?v=v1&t=0s)** welcome to this session today we cover RAG"
        in text
    )
    assert (
        "**[1:10](https://www.youtube.com/watch?v=v1&t=70s)** with Bedrock Knowledge Bases" in text
    )


@pytest.mark.parametrize(
    "kwargs, expected_failed, expected_skipped",
    [
        ({"channel_id": "UCfake"}, 1, 0),  # look-alike channel is rejected loudly
        ({"vtt": None}, 0, 1),  # no captions: skipped
        ({"upload": "20230101"}, 0, 1),  # too old: skipped
    ],
)
def test_rejections(tmp_path, kwargs, expected_failed, expected_skipped):
    f = fetcher(tmp_path, [VideoRef("v1", "Bedrock RAG", 1800)], {"v1": video(**kwargs)})
    report = f.run()
    assert (len(report.failed), report.skipped, report.written) == (
        expected_failed,
        expected_skipped,
        0,
    )


FAKE_YTDLP = """#!/bin/sh
# Stand-in for yt-dlp: validates option syntax like the real tool and writes the files it would.
out=""; mode="video"
while [ $# -gt 0 ]; do
  case "$1" in
    --sleep-subtitles|--sleep-requests) case "$2" in *[!0-9]*) echo "invalid integer value: $2" >&2; exit 2;; esac; shift;;
    -o) out="$2"; shift;;
    -J) mode="list";;
  esac
  shift
done
if [ "$mode" = "list" ]; then
  echo '{"entries": [{"id": "abc", "title": "Bedrock RAG", "duration": 1800}, {"id": null}]}'
else
  echo '{"title": "Bedrock RAG", "channel_id": "UCdoadna9HFHsxXWhafhNvKw", "channel": "AWS Events", "upload_date": "20260301", "duration": 1800, "chapters": []}' > "$out.info.json"
  printf 'WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nhello world\n' > "$out.en.vtt"
fi
"""


def test_ytdlp_source_builds_valid_commands(tmp_path):
    from aipc01_fetch_talks import YtDlpSource

    fake = tmp_path / "yt-dlp"
    fake.write_text(FAKE_YTDLP)
    fake.chmod(0o755)
    source = YtDlpSource(binary=str(fake))
    assert source.list_videos("https://www.youtube.com/@x/videos", 10) == [
        VideoRef("abc", "Bedrock RAG", 1800)
    ]
    data = source.fetch("abc")
    assert (data.title, data.channel_id, data.upload_date) == ("Bedrock RAG", OFFICIAL, "20260301")
    assert "hello world" in data.vtt


def test_rate_limited_calls_are_retried_with_backoff_then_give_up(tmp_path):
    from aipc01_fetch_talks import YtDlpSource

    counter = tmp_path / "n"
    counter.write_text("0")
    fake = tmp_path / "yt-dlp"
    fake.write_text(
        f"#!/bin/sh\nn=$(cat {counter}); echo $((n+1)) > {counter}\n"
        'if [ "$n" -lt 2 ]; then echo "HTTP Error 429: Too Many Requests" >&2; exit 1; fi\n'
        "echo '{\"entries\": []}'\n"
    )
    fake.chmod(0o755)
    sleeps: list[float] = []
    source = YtDlpSource(binary=str(fake), sleep=sleeps.append)
    assert source.list_videos("https://x", 5) == []
    assert sleeps == [30, 90]

    always = tmp_path / "always"
    always.write_text('#!/bin/sh\necho "HTTP Error 429" >&2\nexit 1\n')
    always.chmod(0o755)
    sleeps.clear()
    with pytest.raises(RuntimeError, match="429"):
        YtDlpSource(binary=str(always), sleep=sleeps.append).list_videos("https://x", 5)
    assert sleeps == [30, 90, 180]
