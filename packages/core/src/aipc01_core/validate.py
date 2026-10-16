"""Quality gates applied to every document before it enters the corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from aipc01_core.models import Document

MIN_CHARS_WARNING = 200
_HTML_TAG_RE = re.compile(r"<(?:div|span|script|style|table|nav|iframe)(?=[\s/>])", re.IGNORECASE)
_BOILERPLATE = (
    "Skip to main content",
    "Cookie preferences",
    "Did this page help you?",
    "Sign in to the console",
    "Javascript is disabled",
)
# Page chrome sits on its own line; the same words inside a sentence are legitimate prose.
_BOILERPLATE_RE = re.compile(
    "^[\\s>*#-]*(?:" + "|".join(re.escape(m) for m in _BOILERPLATE) + ")[\\s*.]*$",
    re.IGNORECASE | re.MULTILINE,
)
_FENCED_CODE_RE = re.compile(r"(^|\n)(```|~~~).*?(\n(```|~~~)|\Z)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)


class Level(Enum):
    ERROR = "error"  # document is rejected
    WARNING = "warning"  # document is written but reported


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    level: Level


def validate_document(doc: Document) -> list[Issue]:
    issues: list[Issue] = []
    body = doc.body.strip()
    if not body:
        return [Issue("empty", "document body is empty", Level.ERROR)]
    if not doc.meta.title.strip():
        issues.append(Issue("no-title", "title is empty", Level.ERROR))
    if not doc.meta.source_url.startswith(("http://", "https://")):
        issues.append(Issue("bad-url", f"bad source_url {doc.meta.source_url!r}", Level.ERROR))
    if _HTML_TAG_RE.search(_without_code(body)):
        # Warning only: our converters emit markdown, so remaining tags are almost always
        # legitimate content (HTML samples in indented code, JSON strings, feature docs).
        issues.append(Issue("html-leak", "raw HTML tags left in markdown", Level.WARNING))
    if leaked := _BOILERPLATE_RE.search(body):
        issues.append(
            Issue("boilerplate", f"page chrome leaked: {leaked.group().strip()!r}", Level.ERROR)
        )
    if len(body) < MIN_CHARS_WARNING:
        issues.append(Issue("short", f"only {len(body)} characters", Level.WARNING))
    if not _HEADING_RE.search(body):
        issues.append(Issue("no-heading", "no markdown heading found", Level.WARNING))
    return issues


def _without_code(text: str) -> str:
    """Code samples may legitimately contain HTML; only prose is checked for leaked markup."""
    return _INLINE_CODE_RE.sub("", _FENCED_CODE_RE.sub("\n", text))


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level is Level.ERROR for i in issues)
