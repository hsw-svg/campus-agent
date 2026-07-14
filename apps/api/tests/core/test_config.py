from app.core.config import Settings


def test_models_are_unconfigured_when_settings_are_absent(monkeypatch) -> None:
    for key in (
        "CHAT_BASE_URL",
        "CHAT_API_KEY",
        "CHAT_MODEL",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert settings.chat_is_configured is False
    assert settings.embedding_is_configured is False


def test_chat_configuration_does_not_enable_embedding() -> None:
    settings = Settings(
        chat_base_url="https://models.example/v1",
        chat_api_key="test-key",
        chat_model="chat-model",
    )

    assert settings.chat_is_configured is True
    assert settings.embedding_is_configured is False
