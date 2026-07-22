# Demo Video Script

Target length: 90 to 120 seconds.

## Scene 1

Show Docker stack boot.

Narration:
This project ingests tenant documents, chunks them, stores embeddings in pgvector, and answers only from grounded evidence.

## Scene 2

Open Streamlit UI, select `acme-erp`, upload `closing_policy.md`, wait for processed status.

Narration:
Upload lands in background worker. Extraction, chunking, embeddings, and version activation happen async.

## Scene 3

Ask: `Who approves refunds above 1000 BRL?`

Narration:
Retriever filters by tenant and optional document scope, then answer layer cites exact chunk evidence.

## Scene 4

Ask unrelated question like `What is internship vacation policy?`

Narration:
System refuses to hallucinate and returns no-evidence response when confidence stays below threshold.

## Scene 5

Open conversation history endpoint or UI history panel.

Narration:
Every turn stores retrieval mode, citations, token usage, latency, and audit trail for later review.
