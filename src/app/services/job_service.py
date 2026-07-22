from celery.result import AsyncResult

from app.schemas.jobs import CeleryTaskStatusResponse
from app.workers.celery_app import celery_app


class JobService:
    def get_celery_task_status(self, task_id: str) -> CeleryTaskStatusResponse:
        result = AsyncResult(task_id, app=celery_app)
        payload = result.result if isinstance(result.result, dict) else None
        return CeleryTaskStatusResponse(task_id=task_id, status=result.status.lower(), result=payload)
