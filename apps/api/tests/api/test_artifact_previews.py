from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.artifacts.models import Artifact
from tests.api.conftest import make_workspace


PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def seed_authoritative(client: TestClient, token: str, *, store: bool = True) -> tuple[Artifact, bytes]:
    workspace = client.get("/api/workspaces/current", headers=auth(token)).json()
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    pptx = b"authoritative-pptx"
    artifact = Artifact(
        workspace_id=UUID(workspace["id"]),
        conversation_id=UUID(conversation["id"]),
        type="slide_deck",
        title="Authoritative",
        content="# Authoritative",
        data={"slides": [{"id": "slide-001", "index": 1, "title": "Page"}]},
        format="json",
        object_key="tests/presentation.pptx",
        mime_type=PPTX_MIME,
        sha256=__import__("hashlib").sha256(pptx).hexdigest(),
        size_bytes=len(pptx),
        page_count=1,
    )
    with client.app.state.session_factory() as session:
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        session.expunge(artifact)
    if store:
        client.app.state.object_storage.put(artifact.object_key, pptx)
    return artifact, pptx


def test_authoritative_export_returns_exact_bytes_and_never_falls_back(client: TestClient, monkeypatch) -> None:
    token = make_workspace(client, "teacher")
    artifact, pptx = seed_authoritative(client, token)

    def fail_fallback(*_args, **_kwargs):
        raise AssertionError("authoritative export must not rerender")

    monkeypatch.setattr("app.api.artifacts.SlideDeckPptxSkill.run", fail_fallback)
    response = client.get(
        f"/api/artifacts/{artifact.id}/export", params={"format": "pptx"}, headers=auth(token)
    )
    assert response.status_code == 200
    assert response.content == pptx

    client.app.state.object_storage.delete(artifact.object_key)
    missing = client.get(
        f"/api/artifacts/{artifact.id}/export", params={"format": "pptx"}, headers=auth(token)
    )
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "artifact_presentation_unavailable"


def test_legacy_export_rerenders_from_data(client: TestClient, monkeypatch) -> None:
    token = make_workspace(client, "teacher")
    workspace = client.get("/api/workspaces/current", headers=auth(token)).json()
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    artifact = Artifact(
        workspace_id=UUID(workspace["id"]),
        conversation_id=UUID(conversation["id"]),
        type="slide_deck",
        title="Legacy",
        content="# Legacy",
        data={"slides": [{"id": "s1", "index": 1, "title": "Page 1"}]},
        format="json",
    )
    with client.app.state.session_factory() as session:
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        session.expunge(artifact)

    called = {}

    def mock_run(self, data):
        called["data"] = data

        class Result:
            content = b"rendered-pptx"
            media_type = PPTX_MIME
            extension = "pptx"

        return Result()

    monkeypatch.setattr("app.api.artifacts.SlideDeckPptxSkill.run", mock_run)
    response = client.get(
        f"/api/artifacts/{artifact.id}/export", params={"format": "pptx"}, headers=auth(token)
    )
    assert response.status_code == 200
    assert response.content == b"rendered-pptx"
    assert called["data"] == artifact.data
