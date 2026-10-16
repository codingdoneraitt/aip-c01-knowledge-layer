"""Shared command line for every fetcher package."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from aipc01_core.base import BaseFetcher
from aipc01_core.http import PoliteClient
from aipc01_core.store import DocumentStore

FetcherFactory = Callable[[argparse.Namespace, PoliteClient, DocumentStore], BaseFetcher]


def build_parser(name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"aipc01-fetch-{name}")
    parser.add_argument("--manifest", type=Path, default=Path(f"manifests/{name}.yaml"))
    parser.add_argument("--out", type=Path, default=Path("sources"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/http"))
    parser.add_argument("--limit", type=int, help="fetch at most N targets (for trial runs)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--min-interval", type=float, default=0.25, help="seconds per host")
    parser.add_argument("--refresh", action="store_true", help="ignore the HTTP cache")
    parser.add_argument("--allow-failures", action="store_true", help="exit 0 even if pages failed")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def run_cli(
    name: str,
    factory: FetcherFactory,
    argv: Sequence[str] | None = None,
    extend_parser: Callable[[argparse.ArgumentParser], None] | None = None,
) -> int:
    parser = build_parser(name)
    if extend_parser:
        extend_parser(parser)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    with PoliteClient(
        cache_dir=args.cache_dir, refresh=args.refresh, min_interval=args.min_interval
    ) as client:
        fetcher = factory(args, client, DocumentStore(args.out))
        fetcher.workers = args.workers
        report = fetcher.run(limit=args.limit)
    report.save(args.out / "_reports" / f"{name}.json")
    print(report.summary())
    for failure in (*report.failed, *report.invalid)[:20]:
        print(f"  ! {failure.url}: {failure.reason}", file=sys.stderr)
    bad = report.failed or report.invalid
    return 1 if bad and not args.allow_failures else 0
