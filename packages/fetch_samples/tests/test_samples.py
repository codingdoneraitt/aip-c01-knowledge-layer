import json
import subprocess
from pathlib import Path

import httpx
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_samples import GitCli, SamplesFetcher, SamplesManifest
from aipc01_fetch_samples.fetcher import matches
from aipc01_fetch_samples.licenses import detect_license
from aipc01_fetch_samples.notebook import notebook_to_markdown

MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy"
MIT0 = "MIT No Attribution\n\nPermission is hereby granted, free of charge, to any person"
APACHE = "Apache License\nVersion 2.0, January 2004"
NOTEBOOK = json.dumps(
    {
        "metadata": {"language_info": {"name": "python"}},
        "cells": [
            {"cell_type": "markdown", "source": ["# RAG demo\n", "Intro text."]},
            {
                "cell_type": "code",
                "source": ["import boto3\n", "print(1)"],
                "outputs": [{"text": "SECRET"}],
            },
            {"cell_type": "code", "source": [], "outputs": []},
        ],
    }
)


def make_repo(root: Path, license_text: str) -> Path:
    repo = root / "origin.git-src"
    (repo / "docs").mkdir(parents=True)
    (repo / "LICENSE").write_text(license_text)
    (repo / "README.md").write_text("# Sample repo\n\n" + "Readme body. " * 30)
    (repo / "docs" / "guide.md").write_text("# Guide\n\n" + "Guide body. " * 30)
    (repo / "notes.txt").write_text("ignored")
    (repo / "demo.ipynb").write_text(NOTEBOOK)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        "PATH": "/usr/bin:/bin:/opt/homebrew/bin",
        "HOME": str(root),
    }
    for cmd in (["init", "-b", "main"], ["add", "-A"], ["commit", "-m", "init"]):
        subprocess.run(["git", *cmd], cwd=repo, env=env, check=True, capture_output=True)
    return repo


class LocalGit(GitCli):
    """Resolves 'https://github.com/x/y.git' to a local repo directory."""

    def __init__(self, origin: Path) -> None:
        self.origin = origin

    def sync(self, url: str, dest: Path) -> str:
        return super().sync(f"file://{self.origin}", dest)


def fetcher_for(tmp_path, license_text, allowed=("MIT", "MIT-0", "Apache-2.0"), include=None):
    origin = make_repo(tmp_path, license_text)
    repo = {"id": "demo", "repo": "aws-samples/demo", "exam_domains": [2]}
    if include:
        repo["include"] = include
    manifest = SamplesManifest.model_validate({"allowed_licenses": list(allowed), "repos": [repo]})
    client = PoliteClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    return SamplesFetcher(
        manifest,
        client,
        DocumentStore(tmp_path / "out"),
        clone_dir=tmp_path / "clones",
        git=LocalGit(origin),
    )


def test_detect_license():
    assert detect_license(MIT0) == "MIT-0"
    assert (
        detect_license(
            MIT + "\nThe above copyright notice and this permission notice shall be included"
        )
        == "MIT"
    )
    assert detect_license(APACHE) == "Apache-2.0"
    assert detect_license("proprietary") is None


def test_glob_matching_treats_double_star_as_zero_or_more_dirs():
    assert matches("README.md", ["**/README.md"]) and matches("a/b/README.md", ["**/README.md"])
    assert matches("docs/x/y.md", ["docs/**/*.md"]) and not matches("src/x.md", ["docs/**/*.md"])
    assert matches("docs/guide.md", ["docs/**/*.md"])  # zero intermediate directories
    assert matches("src/aws-x/README.md", ["src/*/README.md"])
    assert not matches("src/a/b/README.md", ["src/*/README.md"])


def test_notebook_conversion_keeps_prose_and_code_but_not_outputs():
    md = notebook_to_markdown(NOTEBOOK)
    assert md.startswith("# RAG demo") and "```python\nimport boto3\nprint(1)\n```" in md
    assert "SECRET" not in md


def test_fetches_matching_files_with_pinned_commit_and_license(tmp_path):
    report = fetcher_for(tmp_path, MIT0).run()
    assert (report.discovered, report.written, report.failed, report.invalid) == (2, 2, [], [])
    out = tmp_path / "out" / "sample" / "demo"
    text = (out / "demo--docs--guide.md").read_text()
    assert "license_note: MIT-0 (github.com/aws-samples/demo)" in text
    assert "/blob/" in text and "path: docs/guide.md" in text


def test_notebooks_are_included_when_requested(tmp_path):
    report = fetcher_for(tmp_path, APACHE, include=["**/*.ipynb"]).run()
    assert report.written == 1
    assert "```python" in (tmp_path / "out/sample/demo/demo--demo.md").read_text()


def test_disallowed_license_skips_repo_and_reports(tmp_path):
    report = fetcher_for(tmp_path, MIT0, allowed=("Apache-2.0",)).run()
    assert report.discovered == 0 and "not in allow list" in report.failed[0].reason


def test_relative_clone_dir_is_resolved_against_the_caller_cwd(tmp_path, monkeypatch):
    origin = make_repo(tmp_path, MIT0)
    monkeypatch.chdir(tmp_path)
    commit = LocalGit(origin).sync("ignored", Path("rel/clone"))
    assert len(commit) == 40 and (tmp_path / "rel/clone/README.md").exists()


def test_license_of_finds_suffixed_license_files(tmp_path):
    from aipc01_fetch_samples.licenses import license_of

    (tmp_path / "LICENSE.APACHE").write_text(APACHE)
    assert license_of(tmp_path) == "Apache-2.0"
    assert license_of(tmp_path / "missing") is None
