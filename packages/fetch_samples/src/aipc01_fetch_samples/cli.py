from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aipc01_core import DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_samples.fetcher import SamplesFetcher
from aipc01_fetch_samples.manifest import SamplesManifest


def _extend(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--clone-dir", default=Path(".cache/git"), type=Path)
    parser.add_argument("--repo", action="append", help="only these repo ids")


def _factory(
    args: argparse.Namespace, client: PoliteClient, store: DocumentStore
) -> SamplesFetcher:
    manifest = load_manifest(args.manifest, SamplesManifest)
    if args.repo:
        manifest = manifest.model_copy(
            update={"repos": [r for r in manifest.repos if r.id in args.repo]}
        )
    return SamplesFetcher(manifest, client, store, clone_dir=args.clone_dir)


def main() -> None:
    sys.exit(run_cli("samples", _factory, extend_parser=_extend))
