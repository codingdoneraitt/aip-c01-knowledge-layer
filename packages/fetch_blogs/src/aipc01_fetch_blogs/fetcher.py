from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from datetime import date
from urllib.parse import urlparse

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.markdown import html_to_markdown
from aipc01_core.sitemap import collect_urls
from bs4 import BeautifulSoup

from aipc01_fetch_blogs.manifest import BlogManifest

log = logging.getLogger(__name__)

CONTENT_SELECTOR = "section.blog-post-content"
_NON_POST_RE = re.compile(r"/(category|tag|author|page)/")
_AUTHORS_RE = re.compile(
    r"^#{2,4}\s+About the authors?\b.*", re.IGNORECASE | re.MULTILINE | re.DOTALL
)


def post_slug(url: str) -> tuple[str, str]:
    """('machine-learning', 'my-post-slug') for https://aws.amazon.com/blogs/machine-learning/my-post-slug/"""
    parts = urlparse(url).path.strip("/").split("/")
    return (parts[1], parts[2]) if len(parts) == 3 and parts[0] == "blogs" else ("", "")


class BlogFetcher(BaseFetcher):
    source = "blogs"

    def __init__(self, manifest: BlogManifest, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.manifest = manifest
        self._include = re.compile(manifest.include, re.IGNORECASE)
        self._exclude = re.compile(manifest.exclude, re.IGNORECASE)

    def wanted(self, url: str) -> bool:
        blog, slug = post_slug(url)
        return (
            blog in self.manifest.blogs
            and not _NON_POST_RE.search(url)
            and bool(self._include.search(slug))
            and not self._exclude.search(slug)
        )

    def discover(self) -> Iterable[Target]:
        urls = collect_urls(lambda u: self.client.get(u).text, self.manifest.sitemap_index)
        selected = [u for u in urls if self.wanted(u)]
        log.info("blogs: %d of %d sitemap urls match", len(selected), len(urls))
        return [Target(u) for u in selected[: self.manifest.max_posts]]

    def fetch(self, target: Target) -> list[Document]:
        soup = BeautifulSoup(self.client.get(target.url).text, "lxml")
        published = _published(soup)
        if published is None or published < self.manifest.published_after:
            return []
        title_el = soup.select_one("h1.blog-post-title")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        blog, slug = post_slug(target.url)
        body = _AUTHORS_RE.sub(
            "", html_to_markdown(str(soup), CONTENT_SELECTOR, target.url)
        ).rstrip()
        meta = DocumentMeta(
            source_url=target.url,
            source_type="blog",
            title=title,
            collection=f"{blog}-blog",
            exam_domains=self.manifest.exam_domains,
            license_note="Public AWS blog post.",
            extra={"published": published.isoformat(), "blog": blog},
        )
        return [
            Document(
                meta=meta, body=f"# {title}\n\n{body}", slug=f"{published:%Y-%m}--{slug[:100]}"
            )
        ]


def _published(soup: BeautifulSoup) -> date | None:
    tag = soup.find("meta", property="article:published_time")
    if not tag or not tag.get("content"):
        return None
    try:
        return date.fromisoformat(str(tag["content"])[:10])
    except ValueError:
        return None
