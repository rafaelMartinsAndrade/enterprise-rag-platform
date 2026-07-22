from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.integrations.mock_answer_provider import MockAnswerProvider
from app.integrations.mock_embedding_provider import MockEmbeddingProvider
from app.integrations.openai_answer_provider import OpenAIAnswerProvider
from app.integrations.openai_embedding_provider import OpenAIEmbeddingProvider


def build_embedding_provider():
    if settings.embedding_provider == "mock":
        return MockEmbeddingProvider()
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider()
    raise ProviderUnavailableError(f"Unsupported embedding provider: {settings.embedding_provider}")


def build_answer_provider():
    if settings.llm_provider == "mock":
        return MockAnswerProvider()
    if settings.llm_provider == "openai":
        return OpenAIAnswerProvider()
    raise ProviderUnavailableError(f"Unsupported answer provider: {settings.llm_provider}")
