import httpx
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_docs import DocsManifest, LlmsSite, LlmsSiteFetcher
from aipc01_fetch_docs.cli import build_fetcher

LLMS = """# Strands Agents

- Agents
  - [Quickstart](https://strands.test/docs/quickstart/index.md): Get started
  - [Hooks](https://strands.test/docs/hooks/index.md)
  - [Blog post](https://strands.test/blog/news/index.md)
- [Quickstart again](https://strands.test/docs/quickstart/index.md)
"""


def handler(request: httpx.Request) -> httpx.Response:
    pages = {
        "/robots.txt": httpx.Response(404),
        "/llms.txt": httpx.Response(200, text=LLMS),
        "/docs/quickstart/index.md": httpx.Response(
            200, text="# Quickstart\n\n" + "Install it. " * 30
        ),
        "/docs/hooks/index.md": httpx.Response(200, text="# Hooks\n\n" + "Use hooks. " * 30),
    }
    return pages.get(request.url.path, httpx.Response(404))


def make(tmp_path):
    site = LlmsSite(
        id="strands",
        title="Strands",
        llms_url="https://strands.test/llms.txt",
        include=r"/docs/",
        exam_domains=[2],
        services=["strands-agents"],
    )
    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0, max_retries=0)
    return LlmsSiteFetcher([site], client, DocumentStore(tmp_path)), client


def test_indented_catalog_entries_are_found_filtered_and_deduplicated(tmp_path):
    fetcher, _ = make(tmp_path)
    assert [t.url for t in fetcher.discover()] == [
        "https://strands.test/docs/quickstart/index.md",
        "https://strands.test/docs/hooks/index.md",
    ]


def test_pages_become_documents_with_site_metadata(tmp_path):
    fetcher, _ = make(tmp_path)
    report = fetcher.run()
    assert (report.written, report.failed, report.invalid) == (2, [], [])
    text = (tmp_path / "docs/strands/strands--docs--hooks.md").read_text()
    assert "title: Hooks" in text and "strands-agents" in text


def test_build_fetcher_filters_by_id_and_combines_guides_and_sites(tmp_path):
    manifest = DocsManifest.model_validate(
        {
            "guides": [
                {"id": "g", "title": "G", "base_url": "https://docs.aws.amazon.com/x/latest/y"}
            ],
            "llms_sites": [
                {"id": "strands", "title": "S", "llms_url": "https://strands.test/llms.txt"}
            ],
        }
    )
    _, client = make(tmp_path)
    store = DocumentStore(tmp_path)
    assert build_fetcher(manifest, client, store).source == "docs"
    assert build_fetcher(manifest, client, store, ["strands"]).source == "llms-sites"
