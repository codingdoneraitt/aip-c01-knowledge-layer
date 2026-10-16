# Lessons Learned

Running log of decisions, surprises, and dead ends. Newest first. Format: what happened, why it matters, what we did.

## 2026-10-16

- **Bedrock web crawler is OpenSearch Serverless only.** It does not support S3 Vectors, so it would break the vector store comparison. We fetch sources ourselves and upload to S3 instead.
- **The awsdocs GitHub repos are archived** (since 2023), so they are stale. We fetch from the live documentation site.
- **AWS docs pages expose a Markdown version** (a `.md` URL variant and a "Markdown" link on the page). This avoids HTML-to-markdown conversion for most docs.
- **Community forums are out of the corpus.** Exam threads often contain recalled exam questions, which breaks the "no braindump" rule, and forum terms restrict reuse.
- **The exam guide is split across many pages.** Overview, 5 domains, technologies, and service lists are separate pages. Domain pages hold the task and skill statements that drive the source manifest.
