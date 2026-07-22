from app.core.db import SessionLocal
from app.services.processing_service import ProcessingService
from app.workers.celery_app import celery_app


@celery_app.task(name="app.process_document_version")
def process_document_version_task(version_id: int) -> dict[str, int | str]:
    with SessionLocal() as session:
        return ProcessingService(session).process_version(version_id)
