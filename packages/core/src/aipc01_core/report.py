"""Run report: what was fetched, skipped and why things failed."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Failure:
    url: str
    reason: str


@dataclass
class FetchReport:
    source: str
    discovered: int = 0
    written: int = 0
    unchanged: int = 0
    skipped: int = 0  # fetched fine but intentionally not kept (e.g. too old)
    failed: list[Failure] = field(default_factory=list)
    invalid: list[Failure] = field(default_factory=list)
    bytes_written: int = 0

    def summary(self) -> str:
        return (
            f"[{self.source}] discovered={self.discovered} written={self.written} "
            f"unchanged={self.unchanged} skipped={self.skipped} failed={len(self.failed)} "
            f"invalid={len(self.invalid)} bytes={self.bytes_written}"
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))
