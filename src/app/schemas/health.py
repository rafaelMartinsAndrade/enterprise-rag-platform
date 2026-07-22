from app.schemas.common import AppBaseModel


class HealthResponse(AppBaseModel):
    status: str
    app: str
    persistence: str
    storage: str
    vector_backend: str
