import httpx
import pytest
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_docs import DocsFetcher, DocsManifest, Guide

BASE = "https://docs.aws.amazon.com/bedrock/latest/userguide"
SITEMAP = (
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    f"<url><loc>{BASE}/a.html</loc></url><url><loc>{BASE}/b.html</loc></url>"
    f"<url><loc>{BASE}/a.html</loc></url><url><loc>{BASE}/doc.pdf</loc></url></urlset>"
)
BODY_A = (
    '\n# Page A\n<a name="a"></a>\n\n' + "Content about knowledge bases. " * 20 + "\nSee [b](b.md)."
)
HTML_B = (
    '<html><body><nav>menu</nav><div id="main-content"><h1>Page B</h1><p>'
    + "Fallback html content. " * 20
    + "</p></div></body></html>"
)


def handler(request: httpx.Request) -> httpx.Response:
    routes = {
        "/robots.txt": httpx.Response(404),
        "/bedrock/latest/userguide/sitemap.xml": httpx.Response(200, text=SITEMAP),
        "/bedrock/latest/userguide/a.md": httpx.Response(200, text=BODY_A),
        "/bedrock/latest/userguide/b.md": httpx.Response(404),
        "/bedrock/latest/userguide/b.html": httpx.Response(200, text=HTML_B),
    }
    return routes.get(request.url.path, httpx.Response(404))


@pytest.fixture
def fetcher(tmp_path):
    guide = Guide(
        id="bedrock-userguide",
        title="Bedrock",
        base_url=BASE + "/",
        exam_domains=[1],
        services=["bedrock"],
    )
    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0)
    return DocsFetcher(DocsManifest(guides=[guide]), client, DocumentStore(tmp_path))


def test_discovers_unique_html_pages_only(fetcher):
    assert [t.url for t in fetcher.discover()] == [f"{BASE}/a.html", f"{BASE}/b.html"]


def test_fetches_markdown_and_falls_back_to_html(fetcher, tmp_path):
    report = fetcher.run()
    assert (report.written, report.failed, report.invalid) == (2, [], [])
    a = (tmp_path / "docs/bedrock-userguide/bedrock-userguide--a.md").read_text()
    assert (
        "title: Page A" in a
        and "(https://docs.aws.amazon.com/bedrock/latest/userguide/b.html)" in a
    )
    assert "<a name" not in a
    b = (tmp_path / "docs/bedrock-userguide/bedrock-userguide--b.md").read_text()
    assert "# Page B" in b and "menu" not in b


def test_missing_sitemap_is_reported_not_raised(tmp_path):
    guide = Guide(id="g", title="G", base_url="https://docs.aws.amazon.com/nope/latest/guide")
    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0, max_retries=0)
    report = DocsFetcher(DocsManifest(guides=[guide]), client, DocumentStore(tmp_path)).run()
    assert report.discovered == 0 and len(report.failed) == 1
