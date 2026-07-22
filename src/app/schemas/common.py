from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AppBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class DocumentStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    deleted = "deleted"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class RetrievalMode(str, Enum):
    vector = "vector"
    hybrid = "hybrid"


class SourceType(str, Enum):
    upload = "upload"
    demo = "demo"


class UsageMetrics(AppBaseModel):
    provider: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: Decimal = Field(ge=0, max_digits=10, decimal_places=6)
    latency_ms: int = Field(ge=0)


class TimestampedResponse(AppBaseModel):
    id: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
