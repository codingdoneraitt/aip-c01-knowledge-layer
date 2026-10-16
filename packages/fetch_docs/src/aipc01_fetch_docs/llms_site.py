from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlparse

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.markdown import clean_markdown, extract_title

from aipc01_fetch_docs.catalog import parse_catalog
from aipc01_fetch_docs.manifest import LlmsSite


class LlmsSiteFetcher(BaseFetcher):
    """Fetches every markdown page listed in a site's `llms.txt` (e.g. strandsagents.com)."""

    source = "llms-sites"

    def __init__(self, sites: list[LlmsSite], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sites = sites

    def discover(self) -> Iterable[Target]:
        for site in self.sites:
            include, exclude = re.compile(site.include), re.compile(site.exclude)
            urls = dict.fromkeys(
                url for _, url, _ in parse_catalog(self.client.get(site.llms_url).text)
            )
            for url in urls:
                if include.search(url) and not exclude.search(url):
                    yield Target(url, {"site": site})

    def fetch(self, target: Target) -> list[Document]:
        site: LlmsSite = target.context["site"]  # type: ignore[assignment]
        body = clean_markdown(self.client.get(target.url).text, base_url=target.url)
        path = urlparse(target.url).path.strip("/").removesuffix(".md").removesuffix("/index")
        meta = DocumentMeta(
            source_url=target.url,
            source_type=site.source_type,
            title=extract_title(body, fallback=path.rsplit("/", 1)[-1]),
            collection=site.id,
            exam_domains=site.exam_domains,
            services=site.services,
            license_note=f"Public docs listed in {urlparse(site.llms_url).netloc}/llms.txt",
        )
        return [Document(meta=meta, body=body, slug=f"{site.id}--{path.replace('/', '--')}"[:180])]
