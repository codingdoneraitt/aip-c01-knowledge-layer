"""Shared building blocks for the AIP-C01 knowledge-layer fetchers."""

from aipc01_core.base import BaseFetcher, CompositeFetcher, Target
from aipc01_core.cli import run_cli
from aipc01_core.http import PoliteClient
from aipc01_core.models import Document, DocumentMeta
from aipc01_core.report import FetchReport
from aipc01_core.store import DocumentStore

__all__ = [
    "BaseFetcher",
    "CompositeFetcher",
    "Document",
    "DocumentMeta",
    "DocumentStore",
    "FetchReport",
    "PoliteClient",
    "Target",
    "run_cli",
]
