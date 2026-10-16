"""Corpus verification: structural integrity of everything under sources/."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from aipc01_core.models import Document, DocumentMeta
from aipc01_core.validate import Level, validate_document

SIDECAR_SUFFIX = ".metadata.json"
_REQUIRED_ATTRS = {"source_url", "source_type", "title", "collection", "fetched"}


@dataclass
class VerifyResult:
    documents: int = 0
    by_collection: Counter = field(default_factory=Counter)
    problems: list[str] = field(default_factory=list)
    warnings: Counter = field(default_factory=Counter)

    @property
    def ok(self) -> bool:
        return not self.problems


def split_frontmatter(text: str) -> tuple[dict, str] | None:
    if not text.startswith("---\n"):
        return None
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        return None
    return yaml.safe_load(head), body.strip()


def verify_tree(root: Path) -> VerifyResult:
    result = VerifyResult()
    hashes: dict[str, list[str]] = defaultdict(list)
    urls: dict[str, list[str]] = defaultdict(list)
    md_files = sorted(
        p
        for p in root.rglob("*.md")
        if not p.name.endswith(SIDECAR_SUFFIX) and "_reports" not in p.parts
    )
    for path in md_files:
        rel = str(path.relative_to(root))
        parsed = split_frontmatter(path.read_text(encoding="utf-8"))
        if parsed is None:
            result.problems.append(f"{rel}: missing or broken frontmatter")
            continue
        front, body = parsed
        result.documents += 1
        stored_hash = front.get("content_hash")
        if stored_hash != hashlib.sha256(body.encode()).hexdigest():
            result.problems.append(f"{rel}: content_hash does not match body")
        try:
            meta = DocumentMeta.model_validate(
                {k: v for k, v in front.items() if k != "content_hash"}
            )
        except ValueError as exc:
            result.problems.append(f"{rel}: invalid metadata ({exc.__class__.__name__})")
            continue
        result.by_collection[f"{meta.source_type}/{meta.collection}"] += 1
        _check_sidecar(path, meta, rel, result)
        for issue in validate_document(Document(meta=meta, body=body)):
            if issue.level is Level.ERROR:
                result.problems.append(f"{rel}: {issue.code}: {issue.message}")
            else:
                result.warnings[issue.code] += 1
        hashes[stored_hash].append(rel)
        urls[meta.source_url].append(rel)
    for url, files in urls.items():
        if len(files) > 1:
            result.problems.append(f"duplicate source_url {url}: {files[:3]}")
    result.warnings["duplicate-body"] = sum(len(f) - 1 for f in hashes.values() if len(f) > 1)
    for sidecar in root.rglob(f"*{SIDECAR_SUFFIX}"):
        if not sidecar.with_name(sidecar.name.removesuffix(SIDECAR_SUFFIX)).exists():
            result.problems.append(f"{sidecar.relative_to(root)}: orphan sidecar")
    return result


def _check_sidecar(path: Path, meta: DocumentMeta, rel: str, result: VerifyResult) -> None:
    sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
    if not sidecar.exists():
        result.problems.append(f"{rel}: missing metadata sidecar")
        return
    try:
        attrs = json.loads(sidecar.read_text())["metadataAttributes"]
    except (ValueError, KeyError):
        result.problems.append(f"{rel}: unreadable metadata sidecar")
        return
    if missing := _REQUIRED_ATTRS - attrs.keys():
        result.problems.append(f"{rel}: sidecar missing {sorted(missing)}")
    elif attrs["source_url"] != meta.source_url:
        result.problems.append(f"{rel}: sidecar source_url differs from frontmatter")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aipc01-verify")
    parser.add_argument("--root", type=Path, default=Path("sources"))
    parser.add_argument("--show", type=int, default=20, help="max problems to print")
    args = parser.parse_args(argv)
    result = verify_tree(args.root)
    print(f"documents: {result.documents}")
    for name, count in sorted(result.by_collection.items()):
        print(f"  {name}: {count}")
    print("warnings:", dict(result.warnings) or "none")
    print(f"problems: {len(result.problems)}")
    for line in result.problems[: args.show]:
        print(f"  ! {line}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
