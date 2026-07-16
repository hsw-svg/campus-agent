from collections.abc import AsyncIterator, Sequence

from fastapi.testclient import TestClient

from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


class FakeChatProvider:
    is_configured = True

    def __init__(self, route_response: str | None = None, deltas: Sequence[str] = ("已处理",)) -> None:
        self.route_response = route_response
        self.deltas = list(deltas)

    async def classify_route(self, messages: list[dict[str, str]]) -> str:
        assert self.route_response is not None
        return self.route_response

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        for delta in self.deltas:
            yield delta


class FailingChatProvider:
    is_configured = True

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        if False:
            yield ""
        raise RuntimeError("temporary upstream failure")


def create_conversation(client: TestClient, token: str) -> dict:
    response = client.post("/api/conversations", json={}, headers=auth(token))
    assert response.status_code == 201
    return response.json()


def read_events(text: str) -> dict[str, dict]:
    events: dict[str, dict] = {}
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_line, data_line = block.split("\n", 1)
        import json

        events[event_line.removeprefix("event: ")] = json.loads(
            data_line.removeprefix("data: ")
        )
    return events


def test_route_endpoint_recognizes_resume_without_crossing_role_boundary(client: TestClient) -> None:
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/route",
        json={"content": "请帮我修改这份简历中的项目经历"},
        headers=auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "resume_helper"
    assert body["selection_source"] == "rule"
    assert body["requires_confirmation"] is False
    assert body["run_id"]


def test_manual_route_records_manual_selection_source(client: TestClient) -> None:
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/route",
        json={"content": "处理这段经历", "agent_id": "resume_helper"},
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "resume_helper"
    assert response.json()["selection_source"] == "manual"


def test_manual_foreign_agent_is_rejected_by_streaming_route(client: TestClient) -> None:
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "处理这份材料", "agent_id": "meeting_minutes"},
        headers=auth(token),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "agent_not_available"


def test_meeting_record_is_routed_to_admin_minutes(client: TestClient) -> None:
    token = make_workspace(client, "admin")
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/route",
        json={"content": "请整理会议记录，提取参会人员、议题、决议和待办。"},
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "meeting_minutes"
    assert response.json()["confidence"] >= 0.8


def test_low_confidence_stream_requires_agent_confirmation(client: TestClient) -> None:
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)
    client.app.state.chat_provider = FakeChatProvider(
        route_response='{"agent":"resume_helper","confidence":0.42,"reason":"可能是求职材料，但证据不足","missing_inputs":[]}'
    )

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "帮我处理一下"},
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    assert events["error"]["code"] == "route_confirmation_required"
    assert "resume_helper" in events["error"]["candidates"]


def test_failed_agent_run_can_be_retried_without_crossing_workspace(client: TestClient) -> None:
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)
    client.app.state.chat_provider = FailingChatProvider()

    failed = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "请帮我修改这份简历"},
        headers=auth(token),
    )
    failed_events = read_events(failed.text)
    run_id = failed_events["message_start"]["run_id"]
    assert failed_events["error"]["code"] == "chat_stream_failed"

    client.app.state.chat_provider = FakeChatProvider(deltas=("重试成功",))
    retried = client.post(f"/api/agent-runs/{run_id}/retry", headers=auth(token))

    assert retried.status_code == 200
    retried_events = read_events(retried.text)
    assert retried_events["done"]["run_id"] == run_id


def test_auto_stream_emits_selected_agent_and_run_id(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = create_conversation(client, token)
    client.app.state.chat_provider = FakeChatProvider(deltas=("学情", "分析结果"))

    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("scores.csv", "匿名编号,章节,得分,满分\nA01,函数,72,100", "text/csv")},
        headers=auth(token),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "分析这份成绩表"},
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    assert events["message_start"]["agent_id"] == "learning_analysis"
    assert events["message_start"]["run_id"]
    assert events["tool_status"]["agent_id"] == "learning_analysis"
    assert events["done"]["run_id"] == events["message_start"]["run_id"]
