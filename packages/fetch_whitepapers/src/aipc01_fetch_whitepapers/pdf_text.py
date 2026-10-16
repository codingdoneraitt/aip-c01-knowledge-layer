"""Cleanup for text extracted from PDFs: drop table-of-contents leaders, running
headers/footers and page numbers that would pollute retrieval chunks."""

from __future__ import annotations

import re
from collections import Counter

_TOC_LEADER_RE = re.compile(r"\.{5,}\s*\d+\s*$")
_PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s+)?\d{1,4}\s*$", re.IGNORECASE)
_COPYRIGHT_RE = re.compile(r"^\s*Copyright ©.*(?:All rights reserved\.?)?\s*$", re.IGNORECASE)
_MAX_REPEAT_LEN = 140
_MIN_REPEATS = 5


def clean_pdf_text(text: str) -> str:
    lines = text.splitlines()
    counts = Counter(line.strip() for line in lines if line.strip())
    repeated = {
        line for line, n in counts.items() if n >= _MIN_REPEATS and len(line) <= _MAX_REPEAT_LEN
    }
    kept = [
        line
        for line in lines
        if not (
            _TOC_LEADER_RE.search(line)
            or _PAGE_NUMBER_RE.match(line)
            or _COPYRIGHT_RE.match(line)
            or line.strip() in repeated
        )
    ]
    return "\n".join(kept)
