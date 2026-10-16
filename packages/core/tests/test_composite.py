import httpx
from aipc01_core import BaseFetcher, CompositeFetcher, DocumentStore, PoliteClient, Target
from aipc01_core.http import NotFound


class Child(BaseFetcher):
    def __init__(self, name, make_doc, *args):
        super().__init__(*args)
        self.source = name
        self.make_doc = make_doc

    def discover(self):
        self.discovery_failures.append(__import__("aipc01_core").report.Failure("sitemap", "gone"))
        return [Target(f"https://example.com/{self.source}")]

    def fetch(self, target):
        return [self.make_doc(source_url=target.url, collection=self.source)]


def test_composite_delegates_to_the_child_that_discovered_the_target(tmp_path, make_doc):
    client = PoliteClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    store = DocumentStore(tmp_path)
    kids = [Child("a", make_doc, client, store), Child("b", make_doc, client, store)]
    report = CompositeFetcher(kids, source="both").run()
    assert (report.discovered, report.written) == (2, 2)
    assert {f.url for f in report.failed} == {"sitemap"}
    assert (tmp_path / "docs/a").exists() and (tmp_path / "docs/b").exists()
    assert NotFound  # imported for parity with other suites
