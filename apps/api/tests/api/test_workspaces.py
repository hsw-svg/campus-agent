from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = create_app(Settings(database_url="sqlite://"))
    app.state.session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with TestClient(app) as test_client:
        yield test_client


def create_workspace(client: TestClient, role: str = "student") -> dict[str, object]:
    response = client.post("/api/workspaces", json={"role": role})

    assert response.status_code == 201
    return response.json()


def test_create_workspace_returns_one_time_token_and_only_persists_its_hash(client: TestClient) -> None:
    first = create_workspace(client, "teacher")
    second = create_workspace(client, "teacher")

    assert first["workspace"]["role"] == "teacher"
    assert first["token"] != second["token"]
    assert len(first["token"]) >= 43

    with client.app.state.session_factory() as session:
        stored = session.get(client.app.state.workspace_model, UUID(first["workspace"]["id"]))
        assert stored is not None
        assert stored.token_hash != first["token"]
        assert len(stored.token_hash) == 64


def test_current_workspace_uses_token_and_ignores_forged_role(client: TestClient) -> None:
    created = create_workspace(client, "teacher")

    response = client.get(
        "/api/workspaces/current",
        headers={"X-Workspace-Token": created["token"], "X-Workspace-Role": "student"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": created["workspace"]["id"], "role": "teacher"}


def test_invalid_or_deleted_token_returns_a_stable_unauthorized_error(client: TestClient) -> None:
    created = create_workspace(client, "admin")
    headers = {"X-Workspace-Token": created["token"]}

    assert client.delete("/api/workspaces/current", headers=headers).status_code == 204

    response = client.get("/api/workspaces/current", headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "workspace_not_found",
            "message": "Workspace credentials are invalid or expired.",
            "details": None,
        }
    }


def test_workspace_tokens_cannot_access_another_workspace(client: TestClient) -> None:
    student = create_workspace(client, "student")
    teacher = create_workspace(client, "teacher")

    student_current = client.get("/api/workspaces/current", headers={"X-Workspace-Token": student["token"]})
    teacher_current = client.get("/api/workspaces/current", headers={"X-Workspace-Token": teacher["token"]})

    assert student_current.json()["id"] != teacher_current.json()["id"]
    assert student_current.json()["role"] == "student"
    assert teacher_current.json()["role"] == "teacher"

    response = client.get(
        f"/api/workspaces/{teacher_current.json()['id']}",
        headers={"X-Workspace-Token": student["token"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"
