import httpx
import pytest
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_blogs import BlogFetcher, BlogManifest
from aipc01_fetch_blogs.fetcher import post_slug

NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
BASE = "https://aws.amazon.com/blogs/machine-learning"
INDEX = f"<sitemapindex {NS}><sitemap><loc>https://aws.amazon.com/s1</loc></sitemap></sitemapindex>"
URLSET = (
    f"<urlset {NS}>"
    + "".join(
        f"<url><loc>{u}</loc></url>"
        for u in [
            f"{BASE}/rag-with-bedrock-knowledge-bases/",
            f"{BASE}/old-rag-post/",
            f"{BASE}/storage-average-fragment/",  # 'rag' only as a substring
            f"{BASE}/category/artificial-intelligence/bedrock/",
            "https://aws.amazon.com/blogs/security/bedrock-guardrails-security/",
            f"{BASE}/bedrock-draft-post-excluded/",
        ]
    )
    + "</urlset>"
)


def post_html(title: str, published: str) -> str:
    return (
        f'<html><head><meta property="article:published_time" content="{published}"></head><body>'
        f'<article><h1 class="blog-post-title">{title}</h1><section class="blog-post-content">'
        f"<p>{'Body text about retrieval. ' * 20}</p><pre><code>aws bedrock list-foundation-models</code></pre>"
        "<h3>About the authors</h3><p>Jane Doe is an SA.</p></section><aside class='blog-comments'>comments</aside></article></body></html>"
    )


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    pages = {
        "/robots.txt": httpx.Response(404),
        "/sitemaps/sitemap_blogs/index/": httpx.Response(200, text=INDEX),
        "/s1": httpx.Response(200, text=URLSET),
        "/blogs/machine-learning/rag-with-bedrock-knowledge-bases/": httpx.Response(
            200, text=post_html("RAG with Bedrock", "2025-03-01T10:00:00-08:00")
        ),
        "/blogs/machine-learning/old-rag-post/": httpx.Response(
            200, text=post_html("Old RAG", "2019-03-01T10:00:00-08:00")
        ),
        "/blogs/security/bedrock-guardrails-security/": httpx.Response(
            200, text=post_html("Guardrails", "2025-06-01T10:00:00-08:00")
        ),
    }
    return pages.get(path, httpx.Response(404))


@pytest.fixture
def fetcher(tmp_path):
    manifest = BlogManifest(
        blogs=["machine-learning", "security"],
        include=r"\b(bedrock|rag|guardrails)\b",
        exclude=r"\bexcluded\b",
        exam_domains=[1],
    )
    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0, max_retries=0)
    return BlogFetcher(manifest, client, DocumentStore(tmp_path))


def test_post_slug():
    assert post_slug(f"{BASE}/abc/") == ("machine-learning", "abc")
    assert post_slug(f"{BASE}/category/x/y/") == ("", "")


def test_discovery_filters_on_slug_blog_and_non_posts(fetcher):
    urls = [t.url for t in fetcher.discover()]
    assert urls == [
        f"{BASE}/rag-with-bedrock-knowledge-bases/",
        f"{BASE}/old-rag-post/",
        "https://aws.amazon.com/blogs/security/bedrock-guardrails-security/",
    ]


def test_old_posts_are_skipped_and_new_ones_stored(fetcher, tmp_path):
    report = fetcher.run()
    assert (report.written, report.skipped, report.failed) == (2, 1, [])
    text = (
        tmp_path / "blog/machine-learning-blog/2025-03--rag-with-bedrock-knowledge-bases.md"
    ).read_text()
    assert "published: '2025-03-01'" in text and "# RAG with Bedrock" in text
    assert "aws bedrock list-foundation-models" in text and "comments" not in text
    assert "About the authors" not in text and "Jane Doe" not in text
