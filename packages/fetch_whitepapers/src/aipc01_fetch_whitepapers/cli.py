from __future__ import annotations

import argparse
import sys

from aipc01_core import DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_whitepapers.fetcher import WhitepaperFetcher
from aipc01_fetch_whitepapers.manifest import WhitepaperManifest


def _factory(
    args: argparse.Namespace, client: PoliteClient, store: DocumentStore
) -> WhitepaperFetcher:
    return WhitepaperFetcher(load_manifest(args.manifest, WhitepaperManifest), client, store)


def main() -> None:
    sys.exit(run_cli("whitepapers", _factory))
