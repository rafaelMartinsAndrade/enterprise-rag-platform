from fastapi import APIRouter

from app.schemas.jobs import CeleryTaskStatusResponse
from app.services.job_service import JobService


router = APIRouter()


@router.get(
    "/celery/{task_id}",
    response_model=CeleryTaskStatusResponse,
    summary="Get Celery task status",
)
def get_celery_task_status(task_id: str) -> CeleryTaskStatusResponse:
    return JobService().get_celery_task_status(task_id)
