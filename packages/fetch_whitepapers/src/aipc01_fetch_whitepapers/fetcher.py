from __future__ import annotations

import io
from collections.abc import Callable, Iterable

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.markdown import clean_markdown

from aipc01_fetch_whitepapers.manifest import Whitepaper, WhitepaperManifest
from aipc01_fetch_whitepapers.pdf_text import clean_pdf_text

PdfConverter = Callable[[bytes], str]
"""Turns PDF bytes into markdown. Injectable so tests need no PDF engine."""


def markitdown_converter(pdf: bytes) -> str:
    from markitdown import MarkItDown  # heavy import, only when actually converting

    result = MarkItDown().convert_stream(io.BytesIO(pdf), file_extension=".pdf")
    return result.text_content


class WhitepaperFetcher(BaseFetcher):
    source = "whitepapers"

    def __init__(
        self,
        manifest: WhitepaperManifest,
        *args,
        converter: PdfConverter = markitdown_converter,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.manifest = manifest
        self.converter = converter

    def discover(self) -> Iterable[Target]:
        for paper in self.manifest.whitepapers:
            yield Target(paper.url, {"paper": paper})

    def fetch(self, target: Target) -> list[Document]:
        paper: Whitepaper = target.context["paper"]  # type: ignore[assignment]
        body = clean_markdown(clean_pdf_text(self.converter(self.client.get(target.url).content)))
        if not body.lstrip().startswith("#"):
            body = f"# {paper.title}\n\n{body}"
        meta = DocumentMeta(
            source_url=paper.url,
            source_type="whitepaper",
            title=paper.title,
            collection=f"{paper.id}-pdf",
            exam_domains=paper.exam_domains,
            services=paper.services,
            license_note="Public AWS publication (PDF).",
            extra={"format": "pdf"},
        )
        return [Document(meta=meta, body=body, slug=paper.id)]
