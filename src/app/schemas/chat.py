from pydantic import Field

from app.schemas.common import AppBaseModel, MessageRole, RetrievalMode, UsageMetrics


class CitationResponse(AppBaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    version_number: int
    page_number: int | None
    section_title: str | None
    excerpt: str
    score: float = Field(ge=0, le=1)


class AskQuestionRequest(AppBaseModel):
    question: str = Field(min_length=5, max_length=1200)
    conversation_id: int | None = Field(default=None, ge=1)
    document_ids: list[int] = Field(default_factory=list, max_length=20)
    retrieval_mode: RetrievalMode = RetrievalMode.hybrid
    top_k: int | None = Field(default=None, ge=1, le=10)
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)


class MessageResponse(AppBaseModel):
    id: int
    role: MessageRole
    content: str
    citations: list[CitationResponse]
    no_evidence: bool


class AnswerResponse(AppBaseModel):
    conversation_id: int
    user_message: MessageResponse
    assistant_message: MessageResponse
    has_sufficient_evidence: bool
    usage: UsageMetrics


class ConversationHistoryResponse(AppBaseModel):
    conversation_id: int
    title: str
    messages: list[MessageResponse]
