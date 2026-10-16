from __future__ import annotations

import argparse
import sys

from aipc01_core import BaseFetcher, DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_guides.fetcher import build_guides_fetcher
from aipc01_fetch_guides.manifest import GuidesManifest


def _factory(args: argparse.Namespace, client: PoliteClient, store: DocumentStore) -> BaseFetcher:
    return build_guides_fetcher(load_manifest(args.manifest, GuidesManifest), client, store)


def main() -> None:
    sys.exit(run_cli("guides", _factory))
