from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainValidationError, NotFoundError
from app.repositories.knowledge_repository import KnowledgeRepository
from app.schemas.auth import TenantContext
from app.schemas.common import DocumentStatus, SourceType
from app.schemas.documents import (
    DocumentActionResponse,
    DocumentDetailResponse,
    DocumentListItem,
    DocumentUploadResponse,
    DocumentVersionResponse,
)
from app.services.storage_service import StorageService
from app.workers.tasks import process_document_version_task


class DocumentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.knowledge_repository = KnowledgeRepository(session)
        self.storage_service = StorageService()

    async def upload_document(
        self,
        *,
        tenant: TenantContext,
        title: str,
        tags: list[str],
        upload,
    ) -> DocumentUploadResponse:
        self._validate_upload(upload)
        document = self.knowledge_repository.create_document(
            organization_id=tenant.organization_id,
            created_by_user_id=tenant.user_id,
            title=title,
            source_type=SourceType.upload.value,
            tags=tags,
        )
        storage_path, checksum, _ = await self.storage_service.save_upload(
            organization_slug=tenant.organization_slug,
            document_id=document.id,
            version_number=1,
            upload=upload,
        )
        version = self.knowledge_repository.create_version(
            organization_id=tenant.organization_id,
            document_id=document.id,
            created_by_user_id=tenant.user_id,
            version_number=1,
            filename=upload.filename or f"document-{document.id}",
            content_type=upload.content_type or "application/octet-stream",
            storage_path=storage_path,
            checksum=checksum,
        )
        self.knowledge_repository.update_document_status(
            document,
            status=DocumentStatus.queued.value,
        )
        async_result = process_document_version_task.delay(version.id)
        self._record_latest_task_id(document=document, task_id=async_result.id)
        return DocumentUploadResponse(
            document_id=document.id,
            version_id=version.id,
            task_id=async_result.id,
            status=DocumentStatus.queued,
        )

    async def update_document(
        self,
        *,
        tenant: TenantContext,
        document_id: int,
        title: str | None,
        tags: list[str] | None,
        upload,
    ) -> DocumentUploadResponse:
        self._validate_upload(upload)
        document = self._get_tenant_document(tenant=tenant, document_id=document_id)
        latest_version = self.knowledge_repository.get_latest_version(document.id)
        next_version_number = 1 if latest_version is None else latest_version.version_number + 1
        if title:
            document.title = title
        if tags is not None:
            document.tags_json = tags
        self.session.add(document)
        self.session.commit()

        storage_path, checksum, _ = await self.storage_service.save_upload(
            organization_slug=tenant.organization_slug,
            document_id=document.id,
            version_number=next_version_number,
            upload=upload,
        )
        if latest_version is not None and latest_version.checksum == checksum:
            raise DomainValidationError("New document version is identical to the latest version.")
        filename = upload.filename or (latest_version.filename if latest_version else f"document-{document.id}")
        version = self.knowledge_repository.create_version(
            organization_id=tenant.organization_id,
            document_id=document.id,
            created_by_user_id=tenant.user_id,
            version_number=next_version_number,
            filename=filename,
            content_type=upload.content_type or "application/octet-stream",
            storage_path=storage_path,
            checksum=checksum,
        )
        self.knowledge_repository.update_document_status(
            document,
            status=DocumentStatus.queued.value,
        )
        async_result = process_document_version_task.delay(version.id)
        self._record_latest_task_id(document=document, task_id=async_result.id)
        return DocumentUploadResponse(
            document_id=document.id,
            version_id=version.id,
            task_id=async_result.id,
            status=DocumentStatus.queued,
        )

    def list_documents(self, *, tenant: TenantContext) -> list[DocumentListItem]:
        return [
            DocumentListItem(
                id=document.id,
                title=document.title,
                status=DocumentStatus(document.status),
                source_type=SourceType(document.source_type),
                current_version_number=document.current_version_number,
                latest_task_id=document.latest_task_id,
                tags=document.tags_json,
            )
            for document in self.knowledge_repository.list_documents(tenant.organization_id)
        ]

    def get_document(self, *, tenant: TenantContext, document_id: int) -> DocumentDetailResponse:
        document = self._get_tenant_document(tenant=tenant, document_id=document_id)
        versions = self.knowledge_repository.list_versions(document.id)
        return DocumentDetailResponse(
            id=document.id,
            title=document.title,
            status=DocumentStatus(document.status),
            source_type=SourceType(document.source_type),
            current_version_number=document.current_version_number,
            latest_task_id=document.latest_task_id,
            latest_error_message=document.latest_error_message,
            tags=document.tags_json,
            versions=[
                DocumentVersionResponse(
                    id=version.id,
                    version_number=version.version_number,
                    filename=version.filename,
                    content_type=version.content_type,
                    processing_status=DocumentStatus(version.processing_status),
                    page_count=version.page_count,
                    character_count=version.character_count,
                    is_active=version.is_active,
                    error_message=version.error_message,
                )
                for version in versions
            ],
        )

    def reprocess_document(self, *, tenant: TenantContext, document_id: int) -> DocumentActionResponse:
        document = self._get_tenant_document(tenant=tenant, document_id=document_id)
        version = self.knowledge_repository.get_active_version(document.id) or self.knowledge_repository.get_latest_version(document.id)
        if version is None:
            raise NotFoundError("Document has no stored version.")
        self.knowledge_repository.update_document_status(document, status=DocumentStatus.queued.value)
        self.knowledge_repository.update_version_processing(version, processing_status=DocumentStatus.queued.value)
        async_result = process_document_version_task.delay(version.id)
        self._record_latest_task_id(document=document, task_id=async_result.id)
        return DocumentActionResponse(
            document_id=document.id,
            status=DocumentStatus.queued,
            task_id=async_result.id,
            detail="Document reprocessing queued.",
        )

    def delete_document(self, *, tenant: TenantContext, document_id: int) -> DocumentActionResponse:
        document = self._get_tenant_document(tenant=tenant, document_id=document_id)
        self.storage_service.delete_document_tree(
            organization_slug=tenant.organization_slug,
            document_id=document.id,
        )
        self.knowledge_repository.delete_document(document)
        return DocumentActionResponse(
            document_id=document_id,
            status=DocumentStatus.deleted,
            detail="Document deleted with vectors and versions.",
        )

    def _get_tenant_document(self, *, tenant: TenantContext, document_id: int):
        document = self.knowledge_repository.get_document(document_id)
        if document is None or document.organization_id != tenant.organization_id:
            raise NotFoundError("Document not found for tenant.")
        return document

    def _validate_upload(self, upload) -> None:
        if upload.content_type not in settings.allowed_upload_types:
            raise DomainValidationError("Unsupported file type for knowledge base ingestion.")

    def _record_latest_task_id(self, *, document, task_id: str) -> None:
        self.session.refresh(document)
        document.latest_task_id = task_id
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
