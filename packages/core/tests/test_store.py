import json

from aipc01_core.store import DocumentStore, WriteResult, slug_from_url, slugify


def test_slugify():
    assert slugify("Hello, World! AWS_Bedrock") == "hello-world-aws-bedrock"
    assert slugify("!!!") == "untitled"


def test_slug_from_url_strips_extension():
    assert slug_from_url("https://docs.aws.amazon.com/bedrock/latest/userguide/kb.html") == (
        "bedrock-latest-userguide-kb"
    )


def test_write_creates_markdown_with_frontmatter_and_sidecar(tmp_path, make_doc):
    store = DocumentStore(tmp_path)
    path, result = store.write(make_doc())
    assert result is WriteResult.WRITTEN
    assert path == tmp_path / "docs" / "x-guide" / "x-latest-guide-page.md"
    text = path.read_text()
    assert text.startswith("---\n") and "source_url:" in text and "content_hash:" in text
    sidecar = json.loads(path.with_name(path.name + ".metadata.json").read_text())
    attrs = sidecar["metadataAttributes"]
    assert attrs["source_type"] == "docs" and attrs["collection"] == "x-guide"


def test_unchanged_content_is_not_rewritten(tmp_path, make_doc):
    store = DocumentStore(tmp_path)
    store.write(make_doc())
    _, result = store.write(make_doc())
    assert result is WriteResult.UNCHANGED


def test_changed_content_is_rewritten(tmp_path, make_doc):
    store = DocumentStore(tmp_path)
    store.write(make_doc())
    _, result = store.write(make_doc(body="# Title\n\nnew body"))
    assert result is WriteResult.WRITTEN


def test_explicit_slug_wins(tmp_path, make_doc):
    doc = make_doc().model_copy(update={"slug": "custom"})
    path, _ = DocumentStore(tmp_path).write(doc)
    assert path.name == "custom.md"


def test_kb_attributes_include_domains_and_services(make_doc):
    doc = make_doc(exam_domains=[1, 5], services=["bedrock"])
    attrs = doc.meta.kb_attributes()
    assert attrs["exam_domains"] == ["1", "5"] and attrs["services"] == ["bedrock"]
