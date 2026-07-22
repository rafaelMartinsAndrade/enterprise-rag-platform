from app.models.llm_execution import LLMExecution
from app.repositories.base import Repository


class LLMExecutionRepository(Repository):
    def create(
        self,
        *,
        organization_id: int,
        operation: str,
        provider: str,
        model: str,
        status: str,
        user_id: int | None = None,
        conversation_id: int | None = None,
        message_id: int | None = None,
        document_id: int | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd=0,
        latency_ms: int = 0,
        request_payload_json: dict | None = None,
        response_payload_json: dict | None = None,
        error_message: str | None = None,
    ) -> LLMExecution:
        record = LLMExecution(
            organization_id=organization_id,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            document_id=document_id,
            operation=operation,
            provider=provider,
            model=model,
            status=status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            latency_ms=latency_ms,
            request_payload_json=request_payload_json or {},
            response_payload_json=response_payload_json or {},
            error_message=error_message,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record
