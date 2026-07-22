from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ProcessingError
from app.core.logging import get_logger
from app.integrations.provider_factory import build_embedding_provider
from app.models.document_chunk import DocumentChunk
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.llm_execution_repository import LLMExecutionRepository
from app.services.chunking_service import ChunkingService
from app.services.text_extraction_service import TextExtractionService


logger = get_logger(__name__)


class ProcessingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.knowledge_repository = KnowledgeRepository(session)
        self.execution_repository = LLMExecutionRepository(session)
        self.text_extraction_service = TextExtractionService()
        self.chunking_service = ChunkingService()

    def process_version(self, version_id: int) -> dict[str, int | str]:
        version = self.knowledge_repository.get_version(version_id)
        if version is None:
            raise NotFoundError("Document version not found.")
        document = self.knowledge_repository.get_document(version.document_id)
        if document is None:
            raise NotFoundError("Document not found.")

        self.knowledge_repository.update_document_status(document, status="processing")
        self.knowledge_repository.update_version_processing(version, processing_status="processing")

        try:
            extracted = self.text_extraction_service.extract(
                storage_path=version.storage_path,
                content_type=version.content_type,
            )
            chunks, strategy = self.chunking_service.chunk_document(extracted)
            embedding_result = None
            stored_chunks: list[DocumentChunk] = []
            if chunks:
                embedding_result = build_embedding_provider().embed_texts([chunk.content for chunk in chunks])
                for chunk, vector in zip(chunks, embedding_result.vectors, strict=True):
                    stored_chunks.append(
                        DocumentChunk(
                            organization_id=document.organization_id,
                            document_id=document.id,
                            document_version_id=version.id,
                            chunk_index=chunk.chunk_index,
                            page_number=chunk.page_number,
                            section_title=chunk.section_title,
                            heading_path=chunk.heading_path,
                            content=chunk.content,
                            search_text=chunk.search_text,
                            metadata_json=chunk.metadata,
                            embedding=vector,
                        )
                    )
                self.knowledge_repository.replace_chunks_for_version(version.id, stored_chunks)
                self.execution_repository.create(
                    organization_id=document.organization_id,
                    document_id=document.id,
                    operation="embedding",
                    provider=embedding_result.usage.provider,
                    model=embedding_result.usage.model,
                    status="succeeded",
                    input_tokens=embedding_result.usage.input_tokens,
                    output_tokens=embedding_result.usage.output_tokens,
                    estimated_cost_usd=embedding_result.usage.estimated_cost_usd,
                    latency_ms=embedding_result.usage.latency_ms,
                    request_payload_json={"chunk_count": len(chunks)},
                    response_payload_json={"stored_chunk_count": len(stored_chunks)},
                )

            self.knowledge_repository.deactivate_other_versions(document.id, version.id)
            self.knowledge_repository.update_version_processing(
                version,
                processing_status="processed",
                page_count=extracted.metadata["page_count"],
                character_count=len(extracted.text),
                extraction_metadata_json=extracted.metadata,
                chunk_strategy_json=strategy,
                is_active=True,
            )
            self.knowledge_repository.update_document_status(
                document,
                status="processed",
                latest_error_message=None,
                current_version_number=version.version_number,
            )
            logger.info(
                "document processed",
                extra={
                    "event": "document_processed",
                    "details": {
                        "document_id": document.id,
                        "version_id": version.id,
                        "chunk_count": len(stored_chunks),
                    },
                },
            )
            return {
                "document_id": document.id,
                "version_id": version.id,
                "chunk_count": len(stored_chunks),
                "status": "processed",
            }
        except Exception as exc:
            error_message = str(exc)
            self.knowledge_repository.update_version_processing(
                version,
                processing_status="failed",
                error_message=error_message,
            )
            self.knowledge_repository.update_document_status(
                document,
                status="failed",
                latest_error_message=error_message,
                current_version_number=document.current_version_number,
            )
            self.execution_repository.create(
                organization_id=document.organization_id,
                document_id=document.id,
                operation="processing",
                provider=settings.embedding_provider,
                model=settings.embedding_model,
                status="failed",
                request_payload_json={"version_id": version.id, "storage_path": Path(version.storage_path).name},
                response_payload_json={},
                error_message=error_message,
            )
            logger.exception(
                "document processing failed",
                extra={
                    "event": "document_processing_failed",
                    "details": {"document_id": document.id, "version_id": version.id},
                },
            )
            raise ProcessingError(
                "Document processing failed.",
                details={"document_id": document.id, "version_id": version.id},
            ) from exc
