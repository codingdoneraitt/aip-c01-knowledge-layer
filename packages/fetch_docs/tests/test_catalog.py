import re

from aipc01_fetch_docs.catalog import guide_id, parse_catalog, select_guides

TEXT = """# AWS Whitepapers

- [AWS CAF for AI AWS Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-caf-for-ai/aws-caf-for-ai.md): Adoption of generative AI. [llms.txt](https://docs.aws.amazon.com/whitepapers/latest/aws-caf-for-ai/llms.txt)
- [Glue Best Practices](https://docs.aws.amazon.com/whitepapers/latest/glue/glue.md)
- [Not markdown](https://example.com/page.html)
"""


def test_parse_catalog_keeps_only_md_entries():
    entries = parse_catalog(TEXT)
    assert [e[1].rsplit("/", 1)[1] for e in entries] == ["aws-caf-for-ai.md", "glue.md"]
    assert entries[0][2] == "Adoption of generative AI."


def test_guide_id_drops_latest():
    assert guide_id("https://docs.aws.amazon.com/whitepapers/latest/aws-caf-for-ai/x.md") == (
        "whitepapers-aws-caf-for-ai"
    )


def test_select_filters_by_keyword_and_sets_metadata():
    guides = select_guides(
        parse_catalog(TEXT),
        re.compile("generative", re.I),
        source_type="whitepaper",
        exam_domains=[1],
    )
    assert len(guides) == 1
    g = guides[0]
    assert g.base_url == "https://docs.aws.amazon.com/whitepapers/latest/aws-caf-for-ai"
    assert (g.source_type, g.exam_domains) == ("whitepaper", [1])
