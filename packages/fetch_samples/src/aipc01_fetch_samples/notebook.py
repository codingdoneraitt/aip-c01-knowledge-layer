"""Jupyter notebook to markdown: prose cells as-is, code cells fenced, outputs dropped."""

from __future__ import annotations

import json


def notebook_to_markdown(raw: str) -> str:
    nb = json.loads(raw)
    language = (
        nb.get("metadata", {}).get("language_info", {}).get("name")
        or nb.get("metadata", {}).get("kernelspec", {}).get("language")
        or "python"
    )
    parts: list[str] = []
    for cell in nb.get("cells", []):
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if not text.strip():
            continue
        if cell.get("cell_type") == "markdown":
            parts.append(text.strip())
        elif cell.get("cell_type") == "code":
            parts.append(f"```{language}\n{text.rstrip()}\n```")
    return "\n\n".join(parts)
