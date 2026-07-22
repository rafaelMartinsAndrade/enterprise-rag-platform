# Enterprise RAG Architecture

```mermaid
flowchart LR
    U["User or Analyst"] --> UI["Streamlit Demo UI"]
    U --> API["FastAPI API"]
    UI --> API
    API --> AUTH["Tenant Auth Headers"]
    API --> DOC["Document Service"]
    API --> CHAT["RAG Service"]
    DOC --> Q["Celery Queue"]
    Q --> WORKER["Processing Worker"]
    WORKER --> EXT["Text Extraction"]
    WORKER --> CHUNK["Chunking + Metadata"]
    WORKER --> EMB["Embedding Provider"]
    EMB --> DB["PostgreSQL + PGVector"]
    CHAT --> RET["Vector or Hybrid Retrieval"]
    RET --> DB
    CHAT --> LLM["Answer Provider"]
    LLM --> API
    DOC --> FILES["Tenant File Storage"]
    WORKER --> FILES
```

## Notes

- Multi-tenant isolation lives in auth dependency, repositories, and retrieval filters.
- Background ingestion keeps upload latency low and makes reprocessing cheap.
- SQLite fallback exists for local tests, but production path is PostgreSQL plus pgvector.
