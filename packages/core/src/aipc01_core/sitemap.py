"""Minimal sitemap.xml parsing (urlset and sitemapindex)."""

from __future__ import annotations

from collections.abc import Callable
from xml.etree import ElementTree

_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def parse_sitemap(xml_text: str) -> tuple[list[str], list[str]]:
    """Return (page_urls, child_sitemap_urls)."""
    root = ElementTree.fromstring(xml_text.encode())
    locs = [el.text.strip() for el in root.iter(f"{_NS}loc") if el.text]
    if root.tag == f"{_NS}sitemapindex":
        return [], locs
    return locs, []


def collect_urls(get_text: Callable[[str], str], sitemap_url: str, max_depth: int = 2) -> list[str]:
    """All page URLs under a sitemap or sitemap index, de-duplicated, in order."""
    pages, children = parse_sitemap(get_text(sitemap_url))
    if max_depth > 0:
        for child in children:
            pages.extend(collect_urls(get_text, child, max_depth - 1))
    return list(dict.fromkeys(pages))
