from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.provider_factory import build_answer_provider, build_embedding_provider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.llm_execution_repository import LLMExecutionRepository
from app.schemas.auth import TenantContext
from app.schemas.chat import (
    AnswerResponse,
    AskQuestionRequest,
    CitationResponse,
    ConversationHistoryResponse,
    MessageResponse,
)
from app.schemas.common import MessageRole, UsageMetrics
from app.services.retrieval_service import RetrievalService


logger = get_logger(__name__)


class RAGService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.execution_repository = LLMExecutionRepository(session)
        self.retrieval_service = RetrievalService(session)

    def ask(self, *, tenant: TenantContext, payload: AskQuestionRequest) -> AnswerResponse:
        conversation = self._get_or_create_conversation(tenant=tenant, payload=payload)
        user_message = self.conversation_repository.create_message(
            organization_id=tenant.organization_id,
            conversation_id=conversation.id,
            user_id=tenant.user_id,
            role=MessageRole.user.value,
            content=payload.question,
            citations=[],
            feedback=None,
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=Decimal("0"),
            prompt_version=settings.prompt_version,
            retrieval_mode=payload.retrieval_mode.value,
            no_evidence=False,
        )

        query_embedding_result = build_embedding_provider().embed_texts([payload.question])
        query_embedding = query_embedding_result.vectors[0]
        self.execution_repository.create(
            organization_id=tenant.organization_id,
            user_id=tenant.user_id,
            conversation_id=conversation.id,
            message_id=user_message.id,
            operation="query_embedding",
            provider=query_embedding_result.usage.provider,
            model=query_embedding_result.usage.model,
            status="succeeded",
            input_tokens=query_embedding_result.usage.input_tokens,
            output_tokens=query_embedding_result.usage.output_tokens,
            estimated_cost_usd=query_embedding_result.usage.estimated_cost_usd,
            latency_ms=query_embedding_result.usage.latency_ms,
            request_payload_json={"question": payload.question},
            response_payload_json={"vector_dimensions": len(query_embedding)},
        )

        retrieved = self.retrieval_service.search(
            organization_id=tenant.organization_id,
            question=payload.question,
            query_embedding=query_embedding,
            retrieval_mode=payload.retrieval_mode,
            document_ids=payload.document_ids,
            top_k=payload.top_k or settings.default_top_k,
        )
        threshold = payload.similarity_threshold or settings.default_similarity_threshold
        evidence = [chunk for chunk in retrieved if chunk.score >= threshold]
        answer_provider = build_answer_provider()

        if not evidence:
            usage = UsageMetrics(
                provider=settings.llm_provider,
                model=settings.llm_model,
                input_tokens=query_embedding_result.usage.input_tokens,
                output_tokens=0,
                estimated_cost_usd=query_embedding_result.usage.estimated_cost_usd,
                latency_ms=query_embedding_result.usage.latency_ms,
            )
            assistant_text = "I could not find enough evidence in current knowledge base for this question."
            self.execution_repository.create(
                organization_id=tenant.organization_id,
                user_id=tenant.user_id,
                conversation_id=conversation.id,
                message_id=user_message.id,
                operation="answer_generation",
                provider=settings.llm_provider,
                model=settings.llm_model,
                status="skipped_no_evidence",
                request_payload_json={"question": payload.question},
                response_payload_json={"reason": "below_similarity_threshold", "threshold": threshold},
            )
            assistant_message = self.conversation_repository.create_message(
                organization_id=tenant.organization_id,
                conversation_id=conversation.id,
                user_id=None,
                role=MessageRole.assistant.value,
                content=assistant_text,
                citations=[],
                feedback=None,
                latency_ms=usage.latency_ms,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                estimated_cost_usd=usage.estimated_cost_usd,
                prompt_version=settings.prompt_version,
                retrieval_mode=payload.retrieval_mode.value,
                no_evidence=True,
            )
            return AnswerResponse(
                conversation_id=conversation.id,
                user_message=MessageResponse(
                    id=user_message.id,
                    role=MessageRole.user,
                    content=user_message.content,
                    citations=[],
                    no_evidence=False,
                ),
                assistant_message=MessageResponse(
                    id=assistant_message.id,
                    role=MessageRole.assistant,
                    content=assistant_message.content,
                    citations=[],
                    no_evidence=True,
                ),
                has_sufficient_evidence=False,
                usage=usage,
            )

        answer_result = answer_provider.generate(question=payload.question, chunks=evidence)
        used_chunks = [chunk for chunk in evidence if chunk.chunk_id in set(answer_result.used_chunk_ids)] or evidence[:3]
        citations = [
            CitationResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                version_number=chunk.version_number,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                excerpt=chunk.excerpt,
                score=chunk.score,
            )
            for chunk in used_chunks
        ]
        self.execution_repository.create(
            organization_id=tenant.organization_id,
            user_id=tenant.user_id,
            conversation_id=conversation.id,
            message_id=user_message.id,
            operation="answer_generation",
            provider=answer_result.usage.provider,
            model=answer_result.usage.model,
            status="succeeded" if answer_result.has_sufficient_evidence else "no_evidence",
            input_tokens=answer_result.usage.input_tokens,
            output_tokens=answer_result.usage.output_tokens,
            estimated_cost_usd=answer_result.usage.estimated_cost_usd,
            latency_ms=answer_result.usage.latency_ms,
            request_payload_json={
                "question": payload.question,
                "candidate_chunk_ids": [chunk.chunk_id for chunk in evidence],
            },
            response_payload_json=answer_result.raw_response,
        )
        assistant_message = self.conversation_repository.create_message(
            organization_id=tenant.organization_id,
            conversation_id=conversation.id,
            user_id=None,
            role=MessageRole.assistant.value,
            content=answer_result.answer,
            citations=[item.model_dump() for item in citations],
            feedback=None,
            latency_ms=answer_result.usage.latency_ms,
            input_tokens=answer_result.usage.input_tokens,
            output_tokens=answer_result.usage.output_tokens,
            estimated_cost_usd=answer_result.usage.estimated_cost_usd,
            prompt_version=settings.prompt_version,
            retrieval_mode=payload.retrieval_mode.value,
            no_evidence=not answer_result.has_sufficient_evidence,
        )
        logger.info(
            "rag answer generated",
            extra={
                "event": "rag_answer_generated",
                "details": {
                    "conversation_id": conversation.id,
                    "user_message_id": user_message.id,
                    "assistant_message_id": assistant_message.id,
                    "citation_count": len(citations),
                },
            },
        )
        return AnswerResponse(
            conversation_id=conversation.id,
            user_message=MessageResponse(
                id=user_message.id,
                role=MessageRole.user,
                content=user_message.content,
                citations=[],
                no_evidence=False,
            ),
            assistant_message=MessageResponse(
                id=assistant_message.id,
                role=MessageRole.assistant,
                content=assistant_message.content,
                citations=citations,
                no_evidence=assistant_message.no_evidence,
            ),
            has_sufficient_evidence=answer_result.has_sufficient_evidence,
            usage=UsageMetrics(
                provider=answer_result.usage.provider,
                model=answer_result.usage.model,
                input_tokens=answer_result.usage.input_tokens,
                output_tokens=answer_result.usage.output_tokens,
                estimated_cost_usd=answer_result.usage.estimated_cost_usd,
                latency_ms=answer_result.usage.latency_ms,
            ),
        )

    def get_conversation_history(
        self,
        *,
        tenant: TenantContext,
        conversation_id: int,
    ) -> ConversationHistoryResponse | None:
        conversation = self.conversation_repository.get(conversation_id)
        if conversation is None or conversation.organization_id != tenant.organization_id:
            return None
        messages = self.conversation_repository.list_messages(conversation_id)
        return ConversationHistoryResponse(
            conversation_id=conversation.id,
            title=conversation.title,
            messages=[
                MessageResponse(
                    id=message.id,
                    role=MessageRole(message.role),
                    content=message.content,
                    citations=[CitationResponse.model_validate(item) for item in message.citations_json],
                    no_evidence=message.no_evidence,
                )
                for message in messages
            ],
        )

    def _get_or_create_conversation(self, *, tenant: TenantContext, payload: AskQuestionRequest):
        if payload.conversation_id is not None:
            existing = self.conversation_repository.get(payload.conversation_id)
            if existing is None or existing.organization_id != tenant.organization_id:
                raise NotFoundError("Conversation not found for tenant.")
            if existing is not None:
                return existing
        return self.conversation_repository.create(
            organization_id=tenant.organization_id,
            user_id=tenant.user_id,
            title=payload.question[:60],
        )
