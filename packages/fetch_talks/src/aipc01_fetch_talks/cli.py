from __future__ import annotations

import argparse
import sys

from aipc01_core import DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_talks.fetcher import TalksFetcher
from aipc01_fetch_talks.manifest import TalksManifest


def _extend(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(workers=2)


def _factory(args: argparse.Namespace, client: PoliteClient, store: DocumentStore) -> TalksFetcher:
    return TalksFetcher(load_manifest(args.manifest, TalksManifest), client, store)


def main() -> None:
    sys.exit(run_cli("talks", _factory, extend_parser=_extend))
