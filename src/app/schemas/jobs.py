from app.schemas.common import AppBaseModel


class CeleryTaskStatusResponse(AppBaseModel):
    task_id: str
    status: str
    result: dict | None = None
