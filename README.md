# Open Study Knowledge Layer for the AWS Generative AI Developer Pro Exam

A retrieval setup on Amazon Bedrock Knowledge Bases, with an MCP server in front, built to study for the AWS Generative AI Developer Pro exam. The goal is to compare retrieval setups on quality and monthly cost, and to publish everything.

> Status: work in progress. Checkboxes below are updated as steps are completed.

## Scope

- **Public sources only:** AWS docs, whitepapers, the official exam guide, and my own notes.
- **No exam questions or braindump material.** Ever.

## Architecture

```
Public sources -> S3 (raw + metadata)
  -> Bedrock Knowledge Bases (one per config)
  -> Retrieve API
  -> MCP server -> any AI client

Eval harness: fixed question set -> each config -> quality, latency, cost
Quiz generator: missed topics -> retrieval -> new practice questions
```

One shared ingestion pipeline feeds every config. Embedding model is fixed, so only chunking and vector store change between configs.

| Config | Vector store | Chunking |
|--------|--------------|----------|
| A | S3 Vectors | Fixed-size |
| B | S3 Vectors | Hierarchical |
| C | S3 Vectors | Semantic |
| D | OpenSearch Serverless | Best of A/B/C |

## Plan

### 1. Setup
- [ ] Redeem AWS credits, set an AWS Budgets alert
- [ ] Choose region and verify Bedrock model access
- [ ] Set up infrastructure as code (one command to deploy and tear down)
- [ ] Tag all resources per config for cost tracking

### 2. Ingest sources
- [ ] Write a source manifest (URL, exam domain, doc type)
- [ ] Build a fetcher: HTML to clean markdown, PDFs as-is
- [ ] Write metadata files (source URL, domain, fetch date)
- [ ] Upload to S3

### 3. Knowledge Bases
- [ ] Create configs A, B, C on S3 Vectors
- [ ] Create config D on OpenSearch Serverless
- [ ] Sync and verify retrieval on each

### 4. MCP server
- [ ] Expose search over all configs
- [ ] Return source citations
- [ ] Test with an AI client

### 5. Evaluation
- [ ] Write a fixed question set from my own notes, with expected source docs
- [ ] Measure retrieval quality (recall@k) and answer quality
- [ ] Measure latency
- [ ] Measure cost: test run and modeled monthly steady state
- [ ] Tear down expensive resources

### 6. Quiz generator
- [ ] Log topics I get wrong
- [ ] Generate practice questions for weak topics from retrieved context

### 7. Publish
- [ ] Clean up code and docs, add license
- [ ] Publish results on AWS Builder Center: what worked, what didn't, what it costs, whether practice scores improved

## Repo layout

To be added as the code lands.

## Disclaimer

Personal project. Not affiliated with or endorsed by AWS. Contains no exam questions or confidential exam content.
