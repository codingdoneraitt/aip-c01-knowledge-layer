from __future__ import annotations

import argparse
import sys

from aipc01_core import DocumentStore, PoliteClient, run_cli
from aipc01_core.manifest import load_manifest

from aipc01_fetch_pricing.fetcher import PricingFetcher
from aipc01_fetch_pricing.manifest import PricingManifest


def _factory(
    args: argparse.Namespace, client: PoliteClient, store: DocumentStore
) -> PricingFetcher:
    return PricingFetcher(load_manifest(args.manifest, PricingManifest), client, store)


def main() -> None:
    sys.exit(run_cli("pricing", _factory))
