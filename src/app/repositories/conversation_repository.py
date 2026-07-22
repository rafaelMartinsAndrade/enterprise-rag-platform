from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.base import Repository


class ConversationRepository(Repository):
    def create(self, *, organization_id: int, user_id: int, title: str) -> Conversation:
        record = Conversation(organization_id=organization_id, user_id=user_id, title=title)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, conversation_id: int) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def create_message(
        self,
        *,
        organization_id: int,
        conversation_id: int,
        user_id: int | None,
        role: str,
        content: str,
        citations: list[dict],
        feedback: str | None,
        latency_ms: int,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd,
        prompt_version: str,
        retrieval_mode: str,
        no_evidence: bool,
    ) -> Message:
        record = Message(
            organization_id=organization_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            citations_json=citations,
            feedback=feedback,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            prompt_version=prompt_version,
            retrieval_mode=retrieval_mode,
            no_evidence=no_evidence,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def list_messages(self, conversation_id: int) -> list[Message]:
        return (
            self.session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.id.asc())
            .all()
        )
