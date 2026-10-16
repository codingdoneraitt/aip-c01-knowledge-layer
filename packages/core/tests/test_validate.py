from aipc01_core.validate import Level, has_errors, validate_document


def codes(doc):
    return {i.code for i in validate_document(doc)}


def test_good_document_has_no_issues(make_doc):
    assert validate_document(make_doc()) == []


def test_empty_body_is_error(make_doc):
    assert codes(make_doc(body="  ")) == {"empty"}


def test_html_leak_and_boilerplate_are_errors(make_doc):
    body = "# T\n\n<div class='x'>hi</div>\nSkip to main content\n" + "x" * 300
    issues = validate_document(make_doc(body=body))
    assert {"html-leak", "boilerplate"} <= {i.code for i in issues}
    assert has_errors(issues)  # boilerplate is the blocking one
    assert next(i for i in issues if i.code == "html-leak").level is Level.WARNING


def test_short_and_headingless_are_warnings_only(make_doc):
    issues = validate_document(make_doc(body="tiny"))
    assert {i.code for i in issues} == {"short", "no-heading"}
    assert not has_errors(issues)
    assert all(i.level is Level.WARNING for i in issues)


def test_bad_url_and_missing_title_are_errors(make_doc):
    assert {"bad-url", "no-title"} <= codes(make_doc(source_url="ftp://x", title=" "))


def test_provide_feedback_heading_is_legitimate_content(make_doc):
    body = "# T\n\n" + "Prose. " * 40 + "\n\n## Provide feedback\n\nUse the thumbs up."
    assert "boilerplate" not in codes(make_doc(body=body))


def test_boilerplate_words_inside_prose_are_fine(make_doc):
    body = "# T\n\nPlease provide feedback on the design. " + "More prose here. " * 20
    assert "boilerplate" not in codes(make_doc(body=body))


def test_html_inside_code_is_not_a_leak(make_doc):
    body = (
        "# T\n\n"
        + "Prose. " * 40
        + "\n\n```html\n<div><script>x()</script></div>\n```\n\nUse `<span>` inline."
    )
    assert "html-leak" not in codes(make_doc(body=body))


def test_unclosed_fence_still_hides_trailing_code_only(make_doc):
    body = "# T\n\n" + "Prose. " * 40 + "\n\n<table><tr></tr></table>\n\n```html\n<div>"
    assert "html-leak" in codes(make_doc(body=body))


def test_placeholders_that_start_like_tags_are_not_html(make_doc):
    body = "# T\n\n" + "Prose. " * 40 + "\n\nEnter <table-name> and <div-id> here."
    assert "html-leak" not in codes(make_doc(body=body))
