from pathlib import Path

from app.core.config import settings
from app.repositories.health_repository import HealthRepository
from app.schemas.health import HealthResponse


class HealthService:
    def __init__(self) -> None:
        self.health_repository = HealthRepository()

    def get_health(self) -> HealthResponse:
        persistence_ok = self.health_repository.check_persistence()
        storage_ok = Path(settings.storage_root).exists()
        vector_backend = "pgvector" if settings.database_url.startswith("postgresql") else "sqlite_json_fallback"
        return HealthResponse(
            status="ok" if persistence_ok and storage_ok else "degraded",
            app="enterprise-rag-platform",
            persistence="reachable" if persistence_ok else "unreachable",
            storage="ready" if storage_ok else "missing",
            vector_backend=vector_backend,
        )
