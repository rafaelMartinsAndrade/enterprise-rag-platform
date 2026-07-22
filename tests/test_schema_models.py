from app.core.config import Settings
from app.schemas.auth import DemoLoginRequest
from app.schemas.chat import AskQuestionRequest
from app.schemas.common import RetrievalMode


def test_settings_and_schema_validation() -> None:
    settings = Settings(
        allowed_upload_types="text/plain, application/pdf",
        api_token="change-me-token",
    )

    assert settings.allowed_upload_types == ["text/plain", "application/pdf"]
    assert DemoLoginRequest(organization_slug="acme-erp", user_email="ana@acme.test").organization_slug == "acme-erp"
    assert AskQuestionRequest(question="Where is refund policy?", retrieval_mode=RetrievalMode.hybrid).retrieval_mode is RetrievalMode.hybrid
