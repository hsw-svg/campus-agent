from collections.abc import AsyncIterator
from pathlib import Path
from typing import Sequence

from fastapi.testclient import TestClient

from app.integrations.storage.local import LocalObjectStorage
from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


class FakeChatProvider:
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield "已根据资料回答"


class FakeEmbeddingProvider:
    is_configured = True

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def create_conversation(client: TestClient, token: str) -> dict:
    response = client.post("/api/conversations", json={}, headers=auth(token))
    assert response.status_code == 201
    return response.json()


def test_upload_parses_and_indexes_text_with_workspace_scope(client: TestClient, tmp_path: Path) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("lesson.md", "线性代数的矩阵秩是本节重点。", "text/markdown")},
        data={"scope": "workspace"},
        headers=auth(token),
    )

    assert response.status_code == 201
    attachment = response.json()
    assert attachment["scope"] == "workspace"
    assert attachment["status"] == "degraded"
    assert attachment["extracted_chars"] > 0
    listed = client.get(
        f"/api/conversations/{conversation['id']}/attachments", headers=auth(token)
    )
    assert [item["id"] for item in listed.json()] == [attachment["id"]]


def test_attachment_and_retrieval_are_isolated_by_workspace(client: TestClient, tmp_path: Path) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")
    student_conversation = create_conversation(client, student)
    teacher_conversation = create_conversation(client, teacher)

    for token, conversation, text in (
        (student, student_conversation, "学生私有资料：量子力学"),
        (teacher, teacher_conversation, "教师私有资料：课堂评价"),
    ):
        response = client.post(
            f"/api/conversations/{conversation['id']}/attachments",
            files={"file": ("material.txt", text, "text/plain")},
            headers=auth(token),
        )
        assert response.status_code == 201

    fake_chat = FakeChatProvider()
    client.app.state.chat_provider = fake_chat
    client.app.state.embedding_provider = FakeEmbeddingProvider()
    response = client.post(
        f"/api/conversations/{teacher_conversation['id']}/messages/stream",
        json={"content": "课堂评价"},
        headers=auth(teacher),
    )
    assert response.status_code == 200
    assert "教师私有资料" in response.text
    assert "学生私有资料" not in response.text
    assert "教师私有资料" in fake_chat.calls[0][0]["content"]
    assert "学生私有资料" not in fake_chat.calls[0][0]["content"]

    forged = client.get(
        f"/api/conversations/{student_conversation['id']}/attachments", headers=auth(teacher)
    )
    assert forged.status_code == 404
