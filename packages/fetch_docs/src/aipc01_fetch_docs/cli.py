from __future__ import annotations

import argparse
import sys

from aipc01_core import BaseFetcher, CompositeFetcher, DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_docs.fetcher import DocsFetcher
from aipc01_fetch_docs.llms_site import LlmsSiteFetcher
from aipc01_fetch_docs.manifest import DocsManifest


def _extend(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--guide", action="append", help="only fetch these guide / site ids")


def build_fetcher(
    manifest: DocsManifest,
    client: PoliteClient,
    store: DocumentStore,
    only: list[str] | None = None,
) -> BaseFetcher:
    guides = [g for g in manifest.guides if not only or g.id in only]
    sites = [s for s in manifest.llms_sites if not only or s.id in only]
    children: list[BaseFetcher] = []
    if guides:
        children.append(DocsFetcher(DocsManifest(guides=guides), client, store))
    if sites:
        children.append(LlmsSiteFetcher(sites, client, store))
    if not children:
        raise SystemExit("no guides or sites selected")
    return children[0] if len(children) == 1 else CompositeFetcher(children, source="docs")


def _factory(args: argparse.Namespace, client: PoliteClient, store: DocumentStore) -> BaseFetcher:
    return build_fetcher(load_manifest(args.manifest, DocsManifest), client, store, args.guide)


def main() -> None:
    sys.exit(run_cli("docs", _factory, extend_parser=_extend))
