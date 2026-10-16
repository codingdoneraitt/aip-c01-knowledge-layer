# Lessons Learned

Running log of decisions, surprises, and dead ends. Newest first. Format: what happened, why it matters, what we did.

## 2026-10-16 (fetch pipeline)

- **Docs have a clean markdown variant.** `docs.aws.amazon.com/<guide>/<page>.md` plus a per-guide `sitemap.xml` and a site-wide `llms.txt` catalog; no scraping of HTML needed for ~20k pages. The `Content-Signal` header explicitly allows AI input.
- **The .md files embed raw HTML tables.** A naive "no HTML in output" check rejected 456 good pages. Fix: convert tables to markdown, ignore code blocks, and treat leftover tags as a warning. Validators need to be tested against the real corpus, not just samples.
- **Boilerplate checks must be line-anchored.** "Provide feedback" is also a real section heading and `<table-name>` placeholders look like tags. Substring checks gave false rejects.
- **Whitepapers and prescriptive guidance are mostly docs guides too**, so one catalog tool (`aipc01-docs-catalog`) generates manifests from `llms.txt` by keyword. PDFs convert to flat text without headings; prefer the HTML/markdown source when both exist.
- **Blog RSS only returns the latest 20 posts and ignores pagination.** The public blog sitemaps (about 91k URLs) plus slug keyword filters are the way to discover relevant posts.
- **Robots and terms differ per host.** docs.aws.amazon.com and aws.amazon.com allow our user agent for these paths; the fetchers honor robots.txt and rate limit per host.
- **Strands Agents docs are not in their GitHub repo** (only examples). The site publishes `llms.txt` with markdown pages, so a generic `llms.txt` fetcher was the right building block.
- **YouTube answers HTTP 429 on the caption endpoint** for unauthenticated yt-dlp from this IP, even for a single video. Retries with backoff are built in; a real run may need a cool-down or cookies.
- **Duplicate and tiny pages exist legitimately** (glossary stubs, copy-pasted Glue connector pages). The verifier reports them as warnings, not errors.

## 2026-10-16

- **Bedrock web crawler is OpenSearch Serverless only.** It does not support S3 Vectors, so it would break the vector store comparison. We fetch sources ourselves and upload to S3 instead.
- **The awsdocs GitHub repos are archived** (since 2023), so they are stale. We fetch from the live documentation site.
- **AWS docs pages expose a Markdown version** (a `.md` URL variant and a "Markdown" link on the page). This avoids HTML-to-markdown conversion for most docs.
- **Community forums are out of the corpus.** Exam threads often contain recalled exam questions, which breaks the "no braindump" rule, and forum terms restrict reuse.
- **The exam guide is split across many pages.** Overview, 5 domains, technologies, and service lists are separate pages. Domain pages hold the task and skill statements that drive the source manifest.
