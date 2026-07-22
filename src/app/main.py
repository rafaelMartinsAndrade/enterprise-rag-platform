from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.middleware import register_middleware
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="1.0.0",
    summary="Multi-tenant enterprise RAG platform for ERP rules, finance procedures, and support knowledge.",
    description=(
        "Enterprise RAG backend with multi-tenant isolation, background ingestion, "
        "pgvector retrieval, grounded answers, citations, and demo-ready operations."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Demo login and tenant context helpers."},
        {"name": "health", "description": "Operational health endpoints."},
        {"name": "organizations", "description": "Organization and user discovery endpoints."},
        {"name": "documents", "description": "Knowledge base document lifecycle endpoints."},
        {"name": "chat", "description": "RAG question answering and history endpoints."},
        {"name": "jobs", "description": "Background processing status endpoints."},
    ],
)
register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)
