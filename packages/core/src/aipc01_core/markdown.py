"""HTML to markdown conversion and markdown cleanup."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import markdownify

_ANCHOR_RE = re.compile(r'<a name="[^"]*"></a>[ \t]*\n?')
_BLANKS_RE = re.compile(r"\n{3,}")
_MD_LINK_RE = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+?)\.md(#[^)\s]*)?\)")
_HTML_TABLE_RE = re.compile(r"<table\b.*?</table>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

_NOISE_SELECTORS = (
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "[role=navigation]",
    "[class*=cookie]",
    "[class*=feedback]",
    "[id*=cookie]",
)


def html_to_markdown(html: str, selector: str | None = None, base_url: str = "") -> str:
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one(selector) if selector else (soup.body or soup)
    if root is None:
        return ""
    for css in _NOISE_SELECTORS:
        for node in root.select(css):
            node.decompose()
    if base_url:
        for tag in root.find_all("a", href=True):
            tag["href"] = _absolute(base_url, str(tag["href"]))
    text = markdownify(str(root), heading_style="ATX", bullets="-", strip=["img"])
    return clean_markdown(text)


def _absolute(base_url: str, href: str) -> str:
    try:
        return urljoin(base_url, href)
    except ValueError:  # malformed href such as "http://[broken"; keep it verbatim
        return href


def clean_markdown(text: str, base_url: str = "") -> str:
    """Remove anchor tags, collapse blank lines, and make relative .md links absolute .html."""
    text = _ANCHOR_RE.sub("", text.replace("\r\n", "\n"))
    text = _HTML_TABLE_RE.sub(lambda m: f"\n\n{_table_to_markdown(m.group())}\n\n", text)
    if base_url:
        text = _MD_LINK_RE.sub(
            lambda m: f"]({urljoin(base_url, m.group(1))}.html{m.group(2) or ''})", text
        )
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return _BLANKS_RE.sub("\n\n", text).strip()


def _table_to_markdown(table_html: str) -> str:
    """AWS .md files embed complex tables as raw HTML; convert them so no tags leak."""
    soup = BeautifulSoup(table_html, "lxml")
    for cell in soup.find_all(["td", "th"]):
        for item in cell.find_all("li"):
            item.insert_before("• ")
            item.append(" ")
            item.unwrap()
        for lst in cell.find_all(["ul", "ol"]):
            lst.unwrap()
    return markdownify(str(soup.table or soup), heading_style="ATX", strip=["img"]).strip()


def extract_title(markdown: str, fallback: str = "") -> str:
    match = _H1_RE.search(markdown)
    return match.group(1).strip() if match else fallback
