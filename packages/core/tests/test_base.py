import httpx
import pytest
from aipc01_core import BaseFetcher, DocumentStore, PoliteClient, Target
from aipc01_core.http import NotFound


class FakeFetcher(BaseFetcher):
    source = "fake"

    def __init__(self, *args, make_doc, **kwargs):
        super().__init__(*args, **kwargs)
        self.make_doc = make_doc

    def discover(self):
        return [Target(f"https://example.com/{n}") for n in ("ok", "missing", "boom", "bad")]

    def fetch(self, target):
        name = target.url.rsplit("/", 1)[1]
        if name == "missing":
            raise NotFound("404")
        if name == "boom":
            raise RuntimeError("kaput")
        if name == "bad":
            return [self.make_doc(body="Skip to main content", source_url=target.url)]
        return [self.make_doc(source_url=target.url)]


@pytest.fixture
def fetcher(tmp_path, make_doc):
    client = PoliteClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    return FakeFetcher(client, DocumentStore(tmp_path), make_doc=make_doc, workers=2)


def test_run_sorts_outcomes_into_report(fetcher):
    report = fetcher.run()
    assert (report.discovered, report.written, report.unchanged) == (4, 1, 0)
    assert {f.url.rsplit("/", 1)[1] for f in report.failed} == {"missing", "boom"}
    assert [f.url.rsplit("/", 1)[1] for f in report.invalid] == ["bad"]


def test_second_run_reports_unchanged(fetcher):
    fetcher.run()
    assert fetcher.run().unchanged == 1


def test_limit_caps_targets(fetcher):
    assert fetcher.run(limit=1).discovered == 1
