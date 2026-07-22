from sqlalchemy import delete

from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.knowledge_document import KnowledgeDocument
from app.repositories.base import Repository


class KnowledgeRepository(Repository):
    def create_document(
        self,
        *,
        organization_id: int,
        created_by_user_id: int,
        title: str,
        source_type: str,
        tags: list[str],
        status: str = "queued",
    ) -> KnowledgeDocument:
        record = KnowledgeDocument(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            title=title,
            source_type=source_type,
            tags_json=tags,
            status=status,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def create_version(
        self,
        *,
        organization_id: int,
        document_id: int,
        created_by_user_id: int,
        version_number: int,
        filename: str,
        content_type: str,
        storage_path: str,
        checksum: str,
        processing_status: str = "queued",
    ) -> DocumentVersion:
        record = DocumentVersion(
            organization_id=organization_id,
            document_id=document_id,
            created_by_user_id=created_by_user_id,
            version_number=version_number,
            filename=filename,
            content_type=content_type,
            storage_path=storage_path,
            checksum=checksum,
            processing_status=processing_status,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_document(self, document_id: int) -> KnowledgeDocument | None:
        return self.session.get(KnowledgeDocument, document_id)

    def get_version(self, version_id: int) -> DocumentVersion | None:
        return self.session.get(DocumentVersion, version_id)

    def list_documents(self, organization_id: int) -> list[KnowledgeDocument]:
        return (
            self.session.query(KnowledgeDocument)
            .filter(KnowledgeDocument.organization_id == organization_id)
            .order_by(KnowledgeDocument.updated_at.desc())
            .all()
        )

    def list_versions(self, document_id: int) -> list[DocumentVersion]:
        return (
            self.session.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .all()
        )

    def get_active_version(self, document_id: int) -> DocumentVersion | None:
        return (
            self.session.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id, DocumentVersion.is_active.is_(True))
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )

    def get_latest_version(self, document_id: int) -> DocumentVersion | None:
        return (
            self.session.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .first()
        )

    def update_document_status(
        self,
        document: KnowledgeDocument,
        *,
        status: str,
        latest_task_id: str | None = None,
        latest_error_message: str | None = None,
        current_version_number: int | None = None,
    ) -> KnowledgeDocument:
        document.status = status
        document.latest_task_id = latest_task_id
        document.latest_error_message = latest_error_message
        document.current_version_number = current_version_number
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def update_version_processing(
        self,
        version: DocumentVersion,
        *,
        processing_status: str,
        page_count: int = 0,
        character_count: int = 0,
        error_message: str | None = None,
        extraction_metadata_json: dict | None = None,
        chunk_strategy_json: dict | None = None,
        is_active: bool | None = None,
    ) -> DocumentVersion:
        version.processing_status = processing_status
        version.page_count = page_count
        version.character_count = character_count
        version.error_message = error_message
        if extraction_metadata_json is not None:
            version.extraction_metadata_json = extraction_metadata_json
        if chunk_strategy_json is not None:
            version.chunk_strategy_json = chunk_strategy_json
        if is_active is not None:
            version.is_active = is_active
        self.session.add(version)
        self.session.commit()
        self.session.refresh(version)
        return version

    def deactivate_other_versions(self, document_id: int, active_version_id: int) -> None:
        versions = (
            self.session.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id)
            .all()
        )
        for version in versions:
            version.is_active = version.id == active_version_id
            self.session.add(version)
        self.session.commit()

    def replace_chunks_for_version(self, version_id: int, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_version_id == version_id))
        self.session.add_all(chunks)
        self.session.commit()
        for chunk in chunks:
            self.session.refresh(chunk)
        return chunks

    def delete_document(self, document: KnowledgeDocument) -> None:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        self.session.execute(delete(DocumentVersion).where(DocumentVersion.document_id == document.id))
        self.session.delete(document)
        self.session.commit()
