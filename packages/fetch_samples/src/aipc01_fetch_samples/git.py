"""Thin git wrapper behind a Protocol so tests can use local repos."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol


class Git(Protocol):
    def sync(self, url: str, dest: Path) -> str:
        """Clone (shallow) or update `dest`, return the checked-out commit sha."""


class GitCli:
    def sync(self, url: str, dest: Path) -> str:
        dest = dest.resolve()  # git runs with a different cwd, so relative paths would drift
        if (dest / ".git").exists():
            self._run("fetch", "--depth", "1", "origin", cwd=dest)
            self._run("reset", "--hard", "FETCH_HEAD", cwd=dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            self._run("clone", "--depth", "1", url, str(dest), cwd=dest.parent)
        return self._run("rev-parse", "HEAD", cwd=dest).strip()

    @staticmethod
    def _run(*args: str, cwd: Path) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env={
                "GIT_TERMINAL_PROMPT": "0",
                "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            },
        )
        if proc.returncode:
            raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()[:300]}")
        return proc.stdout
