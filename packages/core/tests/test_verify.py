import json

from aipc01_core import DocumentStore
from aipc01_core.verify import verify_tree


def test_clean_tree_passes(tmp_path, make_doc):
    DocumentStore(tmp_path).write(make_doc())
    result = verify_tree(tmp_path)
    assert result.ok and result.documents == 1
    assert result.by_collection == {"docs/x-guide": 1}


def test_detects_tampered_body_missing_sidecar_and_orphans(tmp_path, make_doc):
    store = DocumentStore(tmp_path)
    path, _ = store.write(make_doc())
    path.write_text(path.read_text() + "\ntampered")
    other, _ = store.write(make_doc(source_url="https://docs.aws.amazon.com/y/page.html"))
    other.with_name(other.name + ".metadata.json").unlink()
    (tmp_path / "docs" / "x-guide" / "ghost.md.metadata.json").write_text(json.dumps({}))
    problems = "\n".join(verify_tree(tmp_path).problems)
    assert "content_hash does not match" in problems
    assert "missing metadata sidecar" in problems
    assert "orphan sidecar" in problems


def test_duplicate_source_url_is_a_problem(tmp_path, make_doc):
    store = DocumentStore(tmp_path)
    store.write(make_doc().model_copy(update={"slug": "a"}))
    store.write(make_doc().model_copy(update={"slug": "b"}))
    assert any("duplicate source_url" in p for p in verify_tree(tmp_path).problems)


def test_broken_frontmatter(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text("no frontmatter here")
    assert "broken frontmatter" in verify_tree(tmp_path).problems[0]
