from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def configured_settings() -> Settings:
    return Settings(
        chat_base_url="https://models.example/v1",
        chat_api_key="chat-key",
        chat_model="chat-model",
        embedding_base_url="https://models.example/v1",
        embedding_api_key="embedding-key",
        embedding_model="embedding-model",
    )


def test_health_reports_all_healthy_components() -> None:
    app = create_app(configured_settings())
    app.state.database_probe = lambda: None

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "components": {
            "database": {"status": "healthy"},
            "chat_model": {"status": "configured"},
            "embedding_model": {"status": "configured"},
        },
    }


def test_health_stays_readable_when_database_probe_fails() -> None:
    app = create_app(configured_settings())

    def unavailable_database() -> None:
        raise RuntimeError("connection refused")

    app.state.database_probe = unavailable_database

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["components"]["database"] == {
        "status": "unhealthy",
        "detail": "Database connection failed.",
    }


def test_health_includes_deeptutor_without_making_it_a_process_dependency() -> None:
    app = create_app(Settings(deeptutor_enabled=True))
    app.state.database_probe = lambda: None

    class ReadyDeepTutor:
        async def health_check(self) -> dict[str, str]:
            return {"status": "healthy"}

    app.state.deeptutor_client = ReadyDeepTutor()

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["components"]["deep_tutor"] == {"status": "healthy"}
