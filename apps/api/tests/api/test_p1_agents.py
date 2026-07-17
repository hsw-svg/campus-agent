import json
from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from fastapi.testclient import TestClient

from app.integrations.storage.local import LocalObjectStorage
from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def events_from_stream(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_line, data_line = block.split("\n", 1)
        events.append(
            (
                event_line.removeprefix("event: "),
                json.loads(data_line.removeprefix("data: ")),
            )
        )
    return events


class FakeStructuredProvider:
    is_configured = True

    def __init__(self, response: dict) -> None:
        self.response = json.dumps(response, ensure_ascii=False)
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(
        self, messages: Sequence[dict[str, str]]
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield self.response


def create_conversation(client: TestClient, token: str) -> dict:
    response = client.post("/api/conversations", json={}, headers=auth(token))
    assert response.status_code == 201
    return response.json()


def stream(
    client: TestClient,
    conversation_id: str,
    token: str,
    content: str,
    agent_id: str,
    **extra: object,
):
    return client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": content, "agent_id": agent_id, **extra},
        headers=auth(token),
    )


def upload_material(
    client: TestClient, conversation_id: str, token: str, filename: str, content: str
) -> str:
    response = client.post(
        f"/api/conversations/{conversation_id}/attachments",
        files={"file": (filename, content, "text/markdown")},
        headers=auth(token),
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_student_course_qa_requires_explicit_material_and_suppresses_model_call(
    client: TestClient,
) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)
    material_id = upload_material(
        client,
        conversation["id"],
        token,
        "course.md",
        "Python 列表的索引和切片课程资料。",
    )
    provider = FakeStructuredProvider(
        {
            "answer": "不应调用模型",
            "key_points": ["不应调用模型"],
            "follow_up_questions": [],
        }
    )
    client.app.state.chat_provider = provider

    response = stream(client, conversation["id"], token, "解释列表切片", "course_qa")

    assert response.status_code == 200
    events = events_from_stream(response.text)
    error = next(data for name, data in events if name == "error")
    assert error["code"] == "agent_input_incomplete"
    assert provider.calls == []

    response = stream(
        client,
        conversation["id"],
        token,
        "解释列表切片",
        "course_qa",
        selected_attachment_ids=[material_id],
    )
    assert response.status_code == 200
    events = events_from_stream(response.text)
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "course_qa")
    sources = next(data for name, data in events if name == "artifact" and data.get("type") == "sources")
    assert artifact["data"]["answer"] == "不应调用模型"
    assert sources["sources"][0]["filename"] == "course.md"


def test_admin_content_only_request_does_not_implicitly_read_current_upload(
    client: TestClient,
) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    token = make_workspace(client, "admin")
    conversation = create_conversation(client, token)
    upload_material(
        client,
        conversation["id"],
        token,
        "private-admin-note.md",
        "不能被本次未选择请求读取的内部信息。",
    )
    provider = FakeStructuredProvider(
        {
            "topics": ["本次会议"],
            "decisions": [],
            "action_items": [],
        }
    )
    client.app.state.chat_provider = provider

    response = stream(
        client,
        conversation["id"],
        token,
        "整理本次会议：讨论项目进度。",
        "meeting_minutes",
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "meeting_minutes")
    assert artifact["artifact_id"]
    serialized_calls = json.dumps(provider.calls, ensure_ascii=False)
    assert "private-admin-note.md" not in serialized_calls
    assert "不能被本次未选择请求读取" not in serialized_calls

    exported = client.get(
        f"/api/artifacts/{artifact['artifact_id']}/export?format=csv",
        headers=auth(token),
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "topics" in exported.text


def test_selected_attachment_from_another_workspace_is_rejected_before_model_call(
    client: TestClient,
) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    first_token = make_workspace(client, "student")
    second_token = make_workspace(client, "student")
    first_conversation = create_conversation(client, first_token)
    second_conversation = create_conversation(client, second_token)
    foreign_attachment_id = upload_material(
        client,
        first_conversation["id"],
        first_token,
        "foreign.md",
        "其他工作区的课程资料。",
    )
    provider = FakeStructuredProvider(
        {
            "answer": "不应调用模型",
            "key_points": ["不应调用模型"],
            "follow_up_questions": [],
        }
    )
    client.app.state.chat_provider = provider

    response = stream(
        client,
        second_conversation["id"],
        second_token,
        "解释资料",
        "course_qa",
        selected_attachment_ids=[foreign_attachment_id],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "attachment_selection_invalid"
    assert provider.calls == []


def test_invalid_structured_output_is_retryable_as_needs_input(client: TestClient) -> None:
    token = make_workspace(client, "admin")
    conversation = create_conversation(client, token)
    provider = FakeStructuredProvider({"items": [{"owner": "missing task"}]})
    client.app.state.chat_provider = provider

    response = stream(
        client,
        conversation["id"],
        token,
        "拆解发送纪要",
        "todo_breakdown",
    )

    assert response.status_code == 200
    error = next(data for name, data in events_from_stream(response.text) if name == "error")
    assert error["code"] == "invalid_structured_output"
    assert error["retryable"] is False
