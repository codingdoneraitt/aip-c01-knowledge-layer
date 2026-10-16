"""Discover guides from an `llms.txt` catalog (e.g. docs.aws.amazon.com/whitepapers/llms.txt)
and write them as a docs manifest, so new whitepaper / guidance sets need no hand-written YAML."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from aipc01_core import PoliteClient

from aipc01_fetch_docs.manifest import Guide

_LINE_RE = re.compile(r"^\s*- \[(?P<title>[^\]]+)\]\((?P<url>[^)\s]+)\)(?::\s*(?P<desc>.*))?$")
_LLMS_SUFFIX_RE = re.compile(r"\s*\[llms\.txt\]\([^)]*\)\s*$")


def parse_catalog(text: str) -> list[tuple[str, str, str]]:
    """Return (title, first_page_url, description) for each catalog entry."""
    entries = []
    for line in text.splitlines():
        match = _LINE_RE.match(_LLMS_SUFFIX_RE.sub("", line))
        if match and match["url"].endswith(".md"):
            entries.append((match["title"], match["url"], match["desc"] or ""))
    return entries


def guide_id(url: str) -> str:
    parts = [p for p in urlparse(url).path.strip("/").split("/")[:-1] if p != "latest"]
    return "-".join(parts)


def select_guides(
    entries: list[tuple[str, str, str]],
    keywords: re.Pattern[str],
    *,
    source_type: str,
    exam_domains: list[int],
) -> list[Guide]:
    guides, seen = [], set()
    for title, url, desc in entries:
        if not keywords.search(f"{title} {desc}"):
            continue
        base_url = url.rsplit("/", 1)[0]
        if base_url in seen:
            continue
        seen.add(base_url)
        guides.append(
            Guide(
                id=guide_id(url),
                title=title,
                base_url=base_url,
                source_type=source_type,
                exam_domains=exam_domains,
            )
        )
    return guides


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aipc01-docs-catalog")
    parser.add_argument("--llms-url", required=True)
    parser.add_argument(
        "--keywords", required=True, help="case-insensitive regex on title+description"
    )
    parser.add_argument("--source-type", default="whitepaper")
    parser.add_argument("--domain", type=int, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    with PoliteClient() as client:
        entries = parse_catalog(client.get(args.llms_url).text)
    guides = select_guides(
        entries,
        re.compile(args.keywords, re.IGNORECASE),
        source_type=args.source_type,
        exam_domains=args.domain,
    )
    args.out.write_text(
        yaml.safe_dump(
            {"guides": [g.model_dump(exclude_defaults=False) for g in guides]},
            sort_keys=False,
            allow_unicode=True,
        )
    )
    print(f"{len(guides)} of {len(entries)} catalog entries -> {args.out}")
    for g in guides:
        print(f"  {g.id}: {g.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
