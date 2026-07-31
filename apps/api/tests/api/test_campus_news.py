from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_campus_news_defaults_to_neutral_non_clickable_samples() -> None:
    with TestClient(create_app(Settings(database_url="sqlite://"))) as client:
        response = client.get("/api/campus-news")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "sample"
    assert payload["status"] == "fresh"
    assert len(payload["items"]) == 9
    assert {item["category"] for item in payload["items"]} == {"news", "activity", "notice"}
    assert all(item["url"] is None for item in payload["items"])


def test_invalid_nonblank_source_config_degrades_without_samples() -> None:
    settings = Settings(database_url="sqlite://", campus_news_sources_json="not-json")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/campus-news")

    assert response.status_code == 200
    assert response.json() == {
        "mode": "live",
        "status": "degraded",
        "refreshing": False,
        "last_success_at": None,
        "items": [],
    }
