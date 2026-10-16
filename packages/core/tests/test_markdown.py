from aipc01_core.markdown import clean_markdown, extract_title, html_to_markdown


def test_clean_removes_anchors_and_collapses_blank_lines():
    raw = '# Title\n<a name="x"></a>\n\n\n\nText   \n'
    assert clean_markdown(raw) == "# Title\n\nText"


def test_clean_rewrites_relative_md_links_to_absolute_html():
    out = clean_markdown(
        "See [KB](kb-parsing.md#opts) and [web](https://a.com/b.md)",
        base_url="https://docs.aws.amazon.com/bedrock/latest/userguide/x.md",
    )
    assert "(https://docs.aws.amazon.com/bedrock/latest/userguide/kb-parsing.html#opts)" in out
    assert "(https://a.com/b.md)" in out


def test_extract_title():
    assert extract_title("intro\n# My Title\nbody") == "My Title"
    assert extract_title("no heading", "fallback") == "fallback"


def test_html_to_markdown_strips_chrome_and_keeps_content():
    html = """<html><body><nav>Menu</nav><main id="m"><h1>Hi</h1>
    <p>Text <a href="/x">link</a></p><script>bad()</script></main><footer>foot</footer></body></html>"""
    out = html_to_markdown(html, selector="#m", base_url="https://example.com/p")
    assert "# Hi" in out and "[link](https://example.com/x)" in out
    assert "Menu" not in out and "bad()" not in out and "foot" not in out


def test_html_to_markdown_missing_selector_returns_empty():
    assert html_to_markdown("<p>x</p>", selector="#nope") == ""


def test_embedded_html_tables_become_markdown_tables():
    raw = (
        '# T\n\n<table><tbody><tr><td><b>Purpose</b></td><td>Pick <a href="https://a.com">IoT</a>'
        "<ul><li>One</li><li>Two</li></ul></td></tr></tbody></table>\n\nAfter"
    )
    out = clean_markdown(raw)
    assert "<table" not in out and "<td" not in out and "<ul" not in out
    assert "Purpose" in out and "[IoT](https://a.com)" in out and "One" in out and "After" in out


def test_malformed_href_does_not_crash_conversion():
    html = '<main><p><a href="http://[broken">bad</a> and <a href="/ok">ok</a></p></main>'
    out = html_to_markdown(html, "main", "https://example.com/p")
    assert "bad" in out and "https://example.com/ok" in out
