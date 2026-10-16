from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlparse

from aipc01_core import (
    BaseFetcher,
    CompositeFetcher,
    Document,
    DocumentMeta,
    DocumentStore,
    PoliteClient,
    Target,
)
from aipc01_core.markdown import html_to_markdown
from aipc01_core.sitemap import collect_urls
from aipc01_fetch_docs import DocsFetcher, DocsManifest
from bs4 import BeautifulSoup

from aipc01_fetch_guides.manifest import GuidesManifest, Solutions

CONTENT_SELECTOR = "main"


class SolutionsFetcher(BaseFetcher):
    """Solutions Library guidance pages (HTML only, no markdown variant)."""

    source = "solutions"

    def __init__(self, config: Solutions, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config
        self._include = re.compile(config.include, re.IGNORECASE)

    def wanted(self, url: str) -> bool:
        path = urlparse(url).path
        return any(path.startswith(p) for p in self.config.path_prefixes) and bool(
            self._include.search(path.rstrip("/").rsplit("/", 1)[-1])
        )

    def discover(self) -> Iterable[Target]:
        urls = collect_urls(lambda u: self.client.get(u).text, self.config.sitemap)
        return [Target(u) for u in urls if self.wanted(u)]

    def fetch(self, target: Target) -> list[Document]:
        html = self.client.get(target.url).text
        title_tag = BeautifulSoup(html, "lxml").title
        title = (title_tag.string or "").split("|")[0].strip() if title_tag else ""
        body = html_to_markdown(html, CONTENT_SELECTOR, target.url)
        meta = DocumentMeta(
            source_url=target.url,
            source_type="guide",
            title=title,
            collection="solutions-library",
            exam_domains=self.config.exam_domains,
            license_note="Public AWS Solutions Library page.",
        )
        slug = urlparse(target.url).path.rstrip("/").rsplit("/", 1)[-1]
        return [Document(meta=meta, body=f"# {title}\n\n{body}", slug=slug)]


def build_guides_fetcher(
    manifest: GuidesManifest, client: PoliteClient, store: DocumentStore
) -> BaseFetcher:
    children: list[BaseFetcher] = []
    if manifest.docs_guides:
        children.append(DocsFetcher(DocsManifest(guides=manifest.docs_guides), client, store))
    if manifest.solutions:
        children.append(SolutionsFetcher(manifest.solutions, client, store))
    if not children:
        raise ValueError("guides manifest has neither docs_guides nor solutions")
    return CompositeFetcher(children, source="guides")
