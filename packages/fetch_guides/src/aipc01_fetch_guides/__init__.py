"""Fetch AWS decision guides (docs-hosted) and Solutions Library guidance pages."""

from aipc01_fetch_guides.fetcher import SolutionsFetcher, build_guides_fetcher
from aipc01_fetch_guides.manifest import GuidesManifest

__all__ = ["GuidesManifest", "SolutionsFetcher", "build_guides_fetcher"]
