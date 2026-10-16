from aipc01_core.sitemap import collect_urls, parse_sitemap

NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'


def test_urlset():
    xml = f"<urlset {NS}><url><loc> https://a/1.html </loc></url><url><loc>https://a/2.html</loc></url></urlset>"
    assert parse_sitemap(xml) == (["https://a/1.html", "https://a/2.html"], [])


def test_sitemapindex():
    xml = f"<sitemapindex {NS}><sitemap><loc>https://a/s1.xml</loc></sitemap></sitemapindex>"
    assert parse_sitemap(xml) == ([], ["https://a/s1.xml"])


def test_collect_urls_follows_index_and_dedupes():
    docs = {
        "idx": f"<sitemapindex {NS}><sitemap><loc>s1</loc></sitemap><sitemap><loc>s2</loc></sitemap></sitemapindex>",
        "s1": f"<urlset {NS}><url><loc>a</loc></url><url><loc>b</loc></url></urlset>",
        "s2": f"<urlset {NS}><url><loc>b</loc></url><url><loc>c</loc></url></urlset>",
    }
    assert collect_urls(docs.__getitem__, "idx") == ["a", "b", "c"]
