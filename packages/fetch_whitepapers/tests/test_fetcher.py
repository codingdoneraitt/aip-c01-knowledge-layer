import httpx
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_whitepapers import WhitepaperFetcher, WhitepaperManifest

MANIFEST = WhitepaperManifest.model_validate(
    {
        "whitepapers": [
            {
                "id": "wp1",
                "title": "My Paper",
                "url": "https://docs.aws.amazon.com/pdfs/x/wp1.pdf",
                "exam_domains": [3],
                "services": ["bedrock"],
            },
            {"id": "wp2", "title": "Missing", "url": "https://docs.aws.amazon.com/pdfs/x/wp2.pdf"},
        ]
    }
)


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("wp1.pdf"):
        return httpx.Response(200, content=b"%PDF-fake")
    return httpx.Response(404)


def test_converts_pdf_and_prepends_title_when_missing(tmp_path):
    seen = {}

    def converter(pdf: bytes) -> str:
        seen["bytes"] = pdf
        return "Intro paragraph. " * 30 + "\n\n\n\nMore."

    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0, max_retries=0)
    fetcher = WhitepaperFetcher(MANIFEST, client, DocumentStore(tmp_path), converter=converter)
    report = fetcher.run()
    assert seen["bytes"] == b"%PDF-fake"
    assert (report.written, len(report.failed)) == (1, 1)
    text = (tmp_path / "whitepaper/wp1-pdf/wp1.md").read_text()
    assert "\n# My Paper\n" in text and "format: pdf" in text
    assert "\n\n\n" not in text.split("---", 2)[2]
