import httpx
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_guides import GuidesManifest, build_guides_fetcher

NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
DG = "https://docs.aws.amazon.com/decision-guides/latest/decision-guides"
SOL_SITEMAP = (
    f"<urlset {NS}>"
    "<url><loc>https://aws.amazon.com/solutions/guidance/evaluating-generative-ai-apps/</loc></url>"
    "<url><loc>https://aws.amazon.com/solutions/guidance/tape-gateway/</loc></url>"
    "<url><loc>https://aws.amazon.com/solutions/case-studies/gen-ai-customer/</loc></url></urlset>"
)
DG_SITEMAP = f"<urlset {NS}><url><loc>{DG}/genai-guide.html</loc></url></urlset>"
GUIDANCE_HTML = (
    "<html><head><title>Guidance for Evaluating GenAI | AWS Solutions</title></head><body>"
    "<nav>nav</nav><main><h2>Overview</h2><p>"
    + "Evaluation architecture details. " * 20
    + "</p></main></body></html>"
)


def handler(request: httpx.Request) -> httpx.Response:
    routes = {
        "/robots.txt": httpx.Response(404),
        "/sitemaps/sitemap_solutions/": httpx.Response(200, text=SOL_SITEMAP),
        "/solutions/guidance/evaluating-generative-ai-apps/": httpx.Response(
            200, text=GUIDANCE_HTML
        ),
        "/decision-guides/latest/decision-guides/sitemap.xml": httpx.Response(200, text=DG_SITEMAP),
        "/decision-guides/latest/decision-guides/genai-guide.md": httpx.Response(
            200, text="# Choosing a generative AI service\n\n" + "Decision content. " * 30
        ),
    }
    return routes.get(request.url.path, httpx.Response(404))


def test_composite_fetches_decision_guides_and_solutions(tmp_path):
    manifest = GuidesManifest.model_validate(
        {
            "docs_guides": [
                {
                    "id": "decision-guides",
                    "title": "Decision guides",
                    "base_url": DG,
                    "source_type": "guide",
                }
            ],
            "solutions": {"include": "generative-ai"},
        }
    )
    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0, max_retries=0)
    report = build_guides_fetcher(manifest, client, DocumentStore(tmp_path)).run()
    assert (report.discovered, report.written, report.failed, report.invalid) == (2, 2, [], [])
    sol = (tmp_path / "guide/solutions-library/evaluating-generative-ai-apps.md").read_text()
    assert "title: Guidance for Evaluating GenAI" in sol and "nav" not in sol.split("---", 2)[2]
    assert (tmp_path / "guide/decision-guides/decision-guides--genai-guide.md").exists()
