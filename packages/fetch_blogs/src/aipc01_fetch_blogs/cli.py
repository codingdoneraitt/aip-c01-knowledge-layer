from __future__ import annotations

import argparse
import sys

from aipc01_core import DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_blogs.fetcher import BlogFetcher
from aipc01_fetch_blogs.manifest import BlogManifest


def _factory(args: argparse.Namespace, client: PoliteClient, store: DocumentStore) -> BlogFetcher:
    return BlogFetcher(load_manifest(args.manifest, BlogManifest), client, store)


def main() -> None:
    sys.exit(run_cli("blogs", _factory))
