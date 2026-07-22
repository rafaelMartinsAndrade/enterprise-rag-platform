# Enterprise RAG Platform

Multi-tenant enterprise RAG demo. FastAPI API, Celery ingestion, PostgreSQL plus pgvector retrieval, Streamlit UI, grounded answers with citations.

## Scope

Steps covered in this repo:

- business problem, architecture, tenant model
- ingestion, extraction, chunking, embeddings, retrieval, answer generation, citations, history, versioning, reprocessing, hybrid search, reranking
- tests, UI, demo data, architecture artifact, demo video script, publish pack

## Business Problem

Internal teams lose time hunting policy, billing, support, and finance answers across scattered files. This project gives each tenant isolated document ingestion plus grounded Q&A over approved internal knowledge.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Alembic
- Celery plus Redis
- PostgreSQL plus pgvector
- OpenAI SDK or deterministic mock providers
- Streamlit
- Pytest

## Architecture

See [docs/architecture.md](docs/architecture.md).

Core flow:

1. Upload tenant document.
2. Store raw file by tenant and version.
3. Queue background processing.
4. Extract text and page metadata.
5. Chunk with overlap and heading metadata.
6. Generate embeddings and persist chunks.
7. Retrieve by vector or hybrid mode.
8. Generate answer only from retrieved evidence.
9. Return citations and store history plus usage audit.

## Project Layout

```text
src/app/
  api/
  core/
  integrations/
  models/
  repositories/
  schemas/
  scripts/
  services/
  workers/
alembic/
db/init/
demo_data/
docs/
examples/
streamlit_app.py
```

## API Surface

Base prefix: `/api/v1`

Public:

- `GET /health`
- `POST /auth/demo-login`
- `GET /jobs/celery/{task_id}`

Tenant protected with `Authorization`, `X-Organization-Slug`, `X-User-Email`:

- `GET /organizations`
- `GET /organizations/{organization_slug}/users`
- `GET /documents`
- `GET /documents/{document_id}`
- `POST /documents/upload`
- `PUT /documents/{document_id}`
- `POST /documents/{document_id}/reprocess`
- `DELETE /documents/{document_id}`
- `POST /chat/ask`
- `GET /chat/conversations/{conversation_id}`

## Local Run

Copy env:

```bash
cp .env.example .env
```

Install:

```bash
python -m pip install -e ".[dev]"
```

Run migrations:

```bash
alembic upgrade head
```

Seed demo orgs and docs:

```bash
seed-demo
```

Start API:

```bash
uvicorn app.main:app --reload --app-dir src
```

Start worker:

```bash
celery -A app.workers.celery_app:celery_app worker --loglevel=info
```

Start UI:

```bash
streamlit run streamlit_app.py
```

## Docker Run

Boot full stack:

```bash
docker compose up --build
```

Then seed demo data from another shell:

```bash
docker compose exec api seed-demo
```

URLs:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- UI: `http://localhost:8501`

## Demo Assets

- Demo docs: `demo_data/documents/...`
- Curl examples: `examples/`
- Video script: [docs/demo-video-script.md](docs/demo-video-script.md)
- Publish list: [docs/publish-checklist.md](docs/publish-checklist.md)

## Retrieval Modes

- `vector`: pure cosine similarity over pgvector or SQLite fallback.
- `hybrid`: vector score plus keyword overlap rerank.

Tenant and document filters always apply before answer generation.

## Testing

Run:

```bash
pytest
```

Current tests cover:

- health route
- auth and org endpoints
- upload, processing, versioning, deletion
- grounded answers and no-evidence branch
- tenant isolation
- Celery task status
- retrieval path selection

## Production Notes

- Production path expects PostgreSQL plus pgvector.
- SQLite exists only for tests and lightweight local runs.
- `db/init/001-enable-pgvector.sql` enables extension at container init.
- Compose uses official `pgvector/pgvector:pg17` image.
