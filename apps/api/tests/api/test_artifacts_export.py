"""Regression coverage for the /api/artifacts/{id}/export endpoint."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.artifacts.models import Artifact
from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


SAMPLE_DECK_DATA = {
    "topic": "Python 切片",
    "audience": "大二",
    "objective": "掌握切片语法",
    "duration_minutes": 45,
    "context_signals": {
        "learning_analysis": "",
        "weak_points": [],
        "classroom_summary": "",
        "grading": "",
        "job_skill_focus": [],
        "industry_updates": [],
    },
    "slides": [
        {
            "index": 1,
            "layout": "title",
            "title": "Python 切片",
            "subtitle": "45 分钟",
            "bullets": [],
            "notes": "",
            "key_points": [],
            "citations": [],
            "columns": [],
        },
        {
            "index": 2,
            "layout": "bullets",
            "title": "语法",
            "bullets": ["a[1:5]", "a[::-1]"],
            "notes": "",
            "key_points": [],
            "citations": [],
            "columns": [],
            "media": [
                {
                    "kind": "video",
                    "url": "https://example.com/slice-demo.mp4",
                    "title": "切片演示",
                    "caption": "动态演示切片操作",
                    "placement": "inline",
                }
            ],
        },
    ],
    "sources": [],
}


def _seed_slide_deck(client: TestClient, token: str) -> tuple[UUID, UUID]:
    workspace = client.get("/api/workspaces/current", headers=auth(token)).json()
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    with client.app.state.session_factory() as session:
        artifact = Artifact(
            workspace_id=UUID(workspace["id"]),
            conversation_id=UUID(conversation["id"]),
            type="slide_deck",
            title="Python 切片",
            content="# Python 切片\n",
            data=SAMPLE_DECK_DATA,
            format="json",
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        return artifact.id, UUID(workspace["id"])


def test_slide_deck_pptx_export_returns_binary(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    artifact_id, _ = _seed_slide_deck(client, token)

    response = client.get(
        f"/api/artifacts/{artifact_id}/export",
        params={"format": "pptx"},
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert response.content[:2] == b"PK"
    assert f"{artifact_id}.pptx" in response.headers["content-disposition"]


def test_pptx_export_rejects_non_slide_deck(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    workspace = client.get("/api/workspaces/current", headers=auth(token)).json()
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    with client.app.state.session_factory() as session:
        artifact = Artifact(
            workspace_id=UUID(workspace["id"]),
            conversation_id=UUID(conversation["id"]),
            type="learning_analysis",
            title="学情",
            content="# 学情",
            data={"scope": "class"},
            format="markdown",
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        artifact_id = artifact.id

    response = client.get(
        f"/api/artifacts/{artifact_id}/export",
        params={"format": "pptx"},
        headers=auth(token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "artifact_export_format_invalid"


def test_markdown_export_still_works_for_slide_deck(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    artifact_id, _ = _seed_slide_deck(client, token)

    response = client.get(
        f"/api/artifacts/{artifact_id}/export",
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "Python 切片" in response.text
