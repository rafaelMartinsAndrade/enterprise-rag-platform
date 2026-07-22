from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Enterprise RAG Platform", min_length=3, max_length=80)
    app_env: Literal["local", "dev", "staging", "prod"] = "local"
    app_debug: bool = True
    api_v1_prefix: str = Field(default="/api/v1", pattern=r"^/api/v\d+$")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str = Field(default="sqlite:///./rag_platform.db", min_length=10)
    api_token: str = Field(default="change-me", min_length=8)
    default_organization_slug: str = Field(default="acme-erp", min_length=3, max_length=80)
    storage_root: str = Field(default="./data/storage", min_length=3, max_length=255)
    llm_provider: Literal["mock", "openai"] = "mock"
    llm_model: str = Field(default="gpt-4.1-mini", min_length=2, max_length=100)
    llm_api_key: str | None = None
    embedding_provider: Literal["mock", "openai"] = "mock"
    embedding_model: str = Field(default="text-embedding-3-small", min_length=3, max_length=120)
    embedding_dimensions: int = Field(default=1536, ge=8, le=3072)
    prompt_version: str = Field(default="v1-rag-grounded", min_length=2, max_length=60)
    chunk_size_chars: int = Field(default=900, ge=200, le=4000)
    chunk_overlap_chars: int = Field(default=180, ge=0, le=1000)
    default_top_k: int = Field(default=5, ge=1, le=15)
    default_similarity_threshold: float = Field(default=0.2, ge=0, le=1)
    rerank_candidate_count: int = Field(default=8, ge=1, le=20)
    max_upload_size_bytes: int = Field(default=3 * 1024 * 1024, gt=0, le=10 * 1024 * 1024)
    allowed_upload_types: list[str] = Field(
        default_factory=lambda: [
            "text/plain",
            "application/pdf",
            "text/markdown",
            "application/json",
            "text/csv",
        ]
    )
    celery_broker_url: str = Field(default="redis://redis:6379/0", min_length=10)
    celery_result_backend: str = Field(default="redis://redis:6379/1", min_length=10)
    celery_task_always_eager: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("allowed_upload_types", mode="before")
    @classmethod
    def split_allowed_upload_types(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("sqlite:///", "postgresql", "postgresql+psycopg")):
            raise ValueError("Unsupported database URL scheme.")
        return value

    @field_validator("storage_root")
    @classmethod
    def validate_storage_root(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Storage root cannot be blank.")
        return value

    @field_validator("chunk_overlap_chars")
    @classmethod
    def validate_chunk_overlap(cls, value: int, info) -> int:
        chunk_size = info.data.get("chunk_size_chars")
        if chunk_size is not None and value >= chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size.")
        return value


settings = Settings()
