from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[3]


def test_compose_defines_the_single_app_service_and_model_settings() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    environment = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")

    for service in ("db:", "app:"):
        assert service in compose
    assert "8001:8001" not in compose
    assert "DEEPTUTOR_HOME" in compose
    assert "deeptutor_data" in compose
    assert "CHAT_MODEL" in environment
    assert "EMBEDDING_MODEL" in environment
    assert "DEEPTUTOR_VERSION=1.5.8" in environment
