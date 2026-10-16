from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import PurePosixPath

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.http import FetchError, NotFound
from aipc01_core.markdown import clean_markdown, extract_title, html_to_markdown
from aipc01_core.report import Failure
from aipc01_core.sitemap import collect_urls

from aipc01_fetch_docs.manifest import DocsManifest, Guide

log = logging.getLogger(__name__)

HTML_CONTENT_SELECTOR = "#main-content"


class DocsFetcher(BaseFetcher):
    """Crawls each guide's sitemap and fetches the `.md` variant of every page.

    Falls back to converting the HTML page if no markdown variant exists.
    """

    source = "docs"

    def __init__(self, manifest: DocsManifest, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.manifest = manifest

    def discover(self) -> Iterable[Target]:
        for guide in self.manifest.guides:
            try:
                urls = self._page_urls(guide.sitemap_url)
            except FetchError as exc:
                log.warning("sitemap failed for %s: %s", guide.id, exc)
                self.discovery_failures.append(Failure(guide.sitemap_url, str(exc)))
                continue
            log.info("%s: %d pages", guide.id, len(urls))
            for url in urls:
                yield Target(url, {"guide": guide})

    def _page_urls(self, sitemap_url: str) -> list[str]:
        urls = collect_urls(lambda u: self.client.get(u).text, sitemap_url)
        return [u for u in urls if u.endswith(".html")]

    def fetch(self, target: Target) -> list[Document]:
        guide: Guide = target.context["guide"]  # type: ignore[assignment]
        md_url = target.url.removesuffix(".html") + ".md"
        try:
            body = clean_markdown(self.client.get(md_url).text, base_url=md_url)
        except NotFound:
            html = self.client.get(target.url).text
            body = html_to_markdown(html, HTML_CONTENT_SELECTOR, target.url)
        stem = PurePosixPath(target.url.removeprefix(guide.base_url)).stem
        meta = DocumentMeta(
            source_url=target.url,
            source_type=guide.source_type,
            title=extract_title(body, fallback=stem),
            collection=guide.id,
            exam_domains=guide.exam_domains,
            services=guide.services,
            license_note="Public AWS documentation; AWS permits AI use per Content-Signal header.",
        )
        return [Document(meta=meta, body=body, slug=f"{guide.id}--{stem}")]
