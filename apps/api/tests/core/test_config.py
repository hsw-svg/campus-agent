from app.core.config import Settings


def test_models_are_unconfigured_when_settings_are_absent() -> None:
    settings = Settings(
        chat_base_url="",
        chat_api_key="",
        chat_model="",
        embedding_base_url="",
        embedding_api_key="",
        embedding_model="",
    )

    assert settings.chat_is_configured is False
    assert settings.embedding_is_configured is False


def test_chat_configuration_does_not_enable_embedding() -> None:
    settings = Settings(
        chat_base_url="https://models.example/v1",
        chat_api_key="test-key",
        chat_model="chat-model",
        embedding_base_url="",
        embedding_api_key="",
        embedding_model="",
    )

    assert settings.chat_is_configured is True
    assert settings.embedding_is_configured is False


def test_embedding_dimensions_default_matches_local_model() -> None:
    assert Settings().embedding_dimensions == 1024
