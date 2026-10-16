from datetime import date

import pytest
from aipc01_core import Document, DocumentMeta


@pytest.fixture
def make_doc():
    def _make(body: str = "# Title\n\n" + "Some real content. " * 20, **overrides) -> Document:
        meta = {
            "source_url": "https://docs.aws.amazon.com/x/latest/guide/page.html",
            "source_type": "docs",
            "title": "Title",
            "collection": "x-guide",
            "fetched": date(2026, 10, 16),
        }
        meta.update(overrides)
        return Document(meta=DocumentMeta(**meta), body=body)

    return _make
