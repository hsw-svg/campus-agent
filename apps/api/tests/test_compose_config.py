from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[3]


def test_compose_defines_the_stage_one_services_and_model_settings() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    environment = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")

    for service in ("db:", "api:", "web:"):
        assert service in compose
    assert "CHAT_MODEL" in environment
    assert "EMBEDDING_MODEL" in environment
