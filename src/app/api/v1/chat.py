from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_tenant_context
from app.core.db import get_db
from app.schemas.auth import TenantContext
from app.schemas.chat import AnswerResponse, AskQuestionRequest, ConversationHistoryResponse
from app.services.rag_service import RAGService


router = APIRouter()


@router.post(
    "/ask",
    response_model=AnswerResponse,
    summary="Ask grounded question against organization knowledge base",
)
def ask_question(
    payload: AskQuestionRequest,
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    return RAGService(db).ask(tenant=tenant, payload=payload)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history with citations",
)
def get_conversation(
    conversation_id: int,
    tenant: TenantContext = Depends(require_tenant_context),
    db: Session = Depends(get_db),
) -> ConversationHistoryResponse:
    history = RAGService(db).get_conversation_history(tenant=tenant, conversation_id=conversation_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return history
