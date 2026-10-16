from aipc01_fetch_whitepapers.pdf_text import clean_pdf_text


def test_removes_toc_leaders_page_numbers_and_copyright():
    text = "Intro ........ 3\n12\nCopyright © 2026 Amazon Web Services, Inc. All rights reserved.\nReal text"
    assert clean_pdf_text(text) == "Real text"


def test_removes_running_headers_but_keeps_rare_lines():
    header = "AWS Prescriptive Guidance RAG options"
    text = "\n".join([header, "body one", header, "body two", header, header, header, "unique"])
    assert clean_pdf_text(text).splitlines() == ["body one", "body two", "unique"]


def test_long_repeated_lines_are_kept():
    long_line = "x" * 200
    assert clean_pdf_text("\n".join([long_line] * 6)).count("x" * 200) == 6
