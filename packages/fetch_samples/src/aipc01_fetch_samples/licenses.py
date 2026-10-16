"""Tiny SPDX detector for the permissive licenses AWS sample repos use."""

from __future__ import annotations

from pathlib import Path

_LICENSE_GLOBS = ("LICENSE*", "LICENCE*", "COPYING*")


def detect_license(text: str) -> str | None:
    lowered = " ".join(text.lower().split())
    if "mit no attribution" in lowered or (
        "permission is hereby granted, free of charge" in lowered
        and "the above copyright notice and this permission notice shall be included" not in lowered
    ):
        return "MIT-0"
    if "permission is hereby granted, free of charge" in lowered:
        return "MIT"
    if "apache license" in lowered and "version 2.0" in lowered:
        return "Apache-2.0"
    return None


def license_of(repo_dir: Path) -> str | None:
    """SPDX id of the first recognizable top-level license file (LICENSE, LICENSE.APACHE, ...)."""
    for pattern in _LICENSE_GLOBS:
        for path in sorted(repo_dir.glob(pattern)):
            if path.is_file() and (
                spdx := detect_license(path.read_text(encoding="utf-8", errors="replace"))
            ):
                return spdx
    return None
