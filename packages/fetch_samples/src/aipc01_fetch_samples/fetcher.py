from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from functools import cache
from pathlib import Path

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.markdown import clean_markdown, extract_title
from aipc01_core.report import Failure

from aipc01_fetch_samples.git import Git, GitCli
from aipc01_fetch_samples.licenses import license_of
from aipc01_fetch_samples.manifest import Repo, SamplesManifest
from aipc01_fetch_samples.notebook import notebook_to_markdown

log = logging.getLogger(__name__)


@cache
def _glob_regex(pattern: str) -> re.Pattern[str]:
    """Glob to regex: `**/` spans zero or more directories, `*` and `?` stay within one."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(path: str, patterns: list[str]) -> bool:
    return any(_glob_regex(p).match(path) for p in patterns)


class SamplesFetcher(BaseFetcher):
    """Clones each repo, checks its license, converts matching files to documents.

    Does not use the HTTP client: git does the transfer, so robots.txt does not apply.
    """

    source = "samples"

    def __init__(
        self,
        manifest: SamplesManifest,
        *args,
        clone_dir: Path,
        git: Git | None = None,
        remote_base: str = "https://github.com",
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.manifest = manifest
        self.clone_dir = clone_dir
        self.git = git or GitCli()
        self.remote_base = remote_base

    def discover(self) -> Iterable[Target]:
        for repo in self.manifest.repos:
            try:
                yield from self._targets_for(repo)
            except RuntimeError as exc:
                log.warning("repo %s failed: %s", repo.id, exc)
                self.discovery_failures.append(Failure(repo.repo, str(exc)))

    def _targets_for(self, repo: Repo) -> list[Target]:
        dest = self.clone_dir / repo.id
        commit = self.git.sync(f"{self.remote_base}/{repo.repo}.git", dest)
        spdx = license_of(dest)
        if spdx not in self.manifest.allowed_licenses:
            raise RuntimeError(f"license {spdx!r} not in allow list; skipping {repo.repo}")
        paths = sorted(
            str(p.relative_to(dest))
            for p in dest.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(dest).parts
        )
        wanted = [
            p
            for p in paths
            if matches(p, repo.include)
            and not matches(p, repo.exclude)
            and (dest / p).stat().st_size <= repo.max_bytes
        ][: repo.max_files]
        log.info("%s: %d files at %s (%s)", repo.id, len(wanted), commit[:8], spdx)
        return [
            Target(
                f"https://github.com/{repo.repo}/blob/{commit}/{p}",
                {"repo": repo, "path": p, "dest": dest, "license": spdx, "commit": commit},
            )
            for p in wanted
        ]

    def fetch(self, target: Target) -> list[Document]:
        repo: Repo = target.context["repo"]  # type: ignore[assignment]
        path: str = target.context["path"]  # type: ignore[assignment]
        raw = (Path(str(target.context["dest"])) / path).read_text(
            encoding="utf-8", errors="replace"
        )
        text = notebook_to_markdown(raw) if path.endswith(".ipynb") else raw
        body = clean_markdown(text)
        title = extract_title(body, fallback=path)
        meta = DocumentMeta(
            source_url=target.url,
            source_type="sample",
            title=f"{repo.repo}: {title}" if title != path else f"{repo.repo}: {path}",
            collection=repo.id,
            exam_domains=repo.exam_domains,
            services=repo.services,
            license_note=f"{target.context['license']} (github.com/{repo.repo})",
            extra={"repo": repo.repo, "path": path, "commit": str(target.context["commit"])},
        )
        slug = f"{repo.id}--{path.rsplit('.', 1)[0].replace('/', '--')}"[:180]
        return [Document(meta=meta, body=body, slug=slug)]
