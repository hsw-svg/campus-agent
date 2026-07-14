from app.integrations.embedding.providers import OpenAICompatibleEmbeddingProvider
from app.integrations.llm.providers import OpenAICompatibleChatProvider


def test_chat_provider_requires_all_connection_settings() -> None:
    assert OpenAICompatibleChatProvider("", "key", "model").is_configured is False
    assert OpenAICompatibleChatProvider("https://models.example", "", "model").is_configured is False
    assert OpenAICompatibleChatProvider("https://models.example", "key", "").is_configured is False
    assert OpenAICompatibleChatProvider("https://models.example", "key", "model").is_configured is True


def test_embedding_provider_requires_all_connection_settings() -> None:
    assert OpenAICompatibleEmbeddingProvider("https://models.example", "key", "model").is_configured is True
