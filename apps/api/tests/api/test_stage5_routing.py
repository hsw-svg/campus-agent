from collections.abc import AsyncIterator, Sequence
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.intent_retrieval import IntentCandidate
from app.integrations.storage.local import LocalObjectStorage
from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


class FakeChatProvider:
    is_configured = True

    def __init__(self, route_response: str | None = None, deltas: Sequence[str] = ("已处理",)) -> None:
        self.route_response = route_response
        self.deltas = list(deltas)
        self.calls: list[list[dict[str, str]]] = []

    async def classify_route(self, messages: list[dict[str, str]]) -> str:
        assert self.route_response is not None
        return self.route_response

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        for delta in self.deltas:
            yield delta


class StaticCandidateRetriever:
    def __init__(self, *agent_ids: str) -> None:
        self.agent_ids = agent_ids

    async def retrieve(self, query, agents):
        return tuple(
            IntentCandidate(agent_id=agent_id, similarity=0.95 - index * 0.1)
            for index, agent_id in enumerate(self.agent_ids)
        )


class FailingChatProvider:
    is_configured = True

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        if False:
            yield ""
        raise RuntimeError("temporary upstream failure")


class AttachmentAwareRouteClassifier:
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def classify_route(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        payload = json.loads(messages[1]["content"])
        attachments = payload.get("attachments", [])
        has_grade_sheet = any("寰楀垎" in json.dumps(item, ensure_ascii=False) for item in attachments)
        agent = "learning_analysis" if has_grade_sheet else "lesson_design"
        return json.dumps(
            {
                "agent": agent,
                "confidence": 0.92,
                "reason": "route by attachment scope",
                "missing_inputs": [],
            },
            ensure_ascii=False,
        )


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
    client.app.state.intent_candidate_retriever = StaticCandidateRetriever(
        "resume_helper", "study_planner", "personal_tutor"
    )
    client.app.state.chat_provider = FakeChatProvider(
        route_response='{"agent":"resume_helper","confidence":0.95,"reason":"请求是简历优化"}'
    )

    response = client.post(
        f"/api/conversations/{conversation['id']}/route",
        json={"content": "请帮我修改这份简历中的项目经历"},
        headers=auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "resume_helper"
    assert body["selection_source"] == "semantic_llm"
    assert body["requires_confirmation"] is False
    assert body["candidate_agent_ids"] == [
        "resume_helper",
        "study_planner",
        "personal_tutor",
    ]
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
    client.app.state.chat_provider = FakeChatProvider(
        route_response='{"agent":"meeting_minutes","confidence":0.94,"reason":"请求整理会议纪要"}'
    )

    response = client.post(
        f"/api/conversations/{conversation['id']}/route",
        json={"content": "请整理会议记录，提取参会人员、议题、决议和待办。"},
        headers=auth(token),
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "meeting_minutes"
    assert response.json()["confidence"] >= 0.8


def test_low_confidence_stream_falls_back_to_generic_chat(client: TestClient) -> None:
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
    assert events["message_start"]["agent_id"] is None
    assert events["route_decision"]["selection_source"] == "fallback"
    assert events["done"]["run_id"] == events["message_start"]["run_id"]
    assert "error" not in events


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
    client.app.state.chat_provider = FakeChatProvider(
        route_response='{"agent":"learning_analysis","confidence":0.96,"reason":"请求分析匿名成绩表"}',
        deltas=("学情", "分析结果"),
    )

    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("scores.csv", "匿名编号,章节,得分,满分\nA01,函数,72,100", "text/csv")},
        headers=auth(token),
    )
    assert upload.status_code == 201
    selected_attachment_id = upload.json()["id"]

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "分析这份成绩表", "selected_attachment_ids": [selected_attachment_id]},
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    assert events["message_start"]["agent_id"] == "learning_analysis"
    assert events["message_start"]["run_id"]
    assert events["tool_status"]["agent_id"] == "learning_analysis"
    assert events["done"]["run_id"] == events["message_start"]["run_id"]


def test_stream_preserves_course_workflow_context_in_run_events(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = create_conversation(client, token)
    client.app.state.chat_provider = FakeChatProvider(deltas=("已关联课程",))

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={
            "content": "分析这份成绩表",
            "course_id": "python-programming",
            "workflow_id": "learning-analysis-to-activity",
            "input_refs": ["attachment:demo"],
        },
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    assert events["message_start"]["course_id"] == "python-programming"
    assert events["message_start"]["workflow_id"] == "learning-analysis-to-activity"


def test_stream_rejects_parent_run_from_another_conversation(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    first_conversation = create_conversation(client, token)
    second_conversation = create_conversation(client, token)
    client.app.state.chat_provider = FakeChatProvider(deltas=("第一步",))

    first = client.post(
        f"/api/conversations/{first_conversation['id']}/messages/stream",
        json={"content": "生成第一步"},
        headers=auth(token),
    )
    parent_run_id = read_events(first.text)["message_start"]["run_id"]

    chained = client.post(
        f"/api/conversations/{second_conversation['id']}/messages/stream",
        json={"content": "生成下一步", "parent_run_id": parent_run_id},
        headers=auth(token),
    )

    assert chained.status_code == 422
    assert chained.json()["error"]["code"] == "parent_run_not_found"


def test_new_conversation_ignores_previous_workspace_attachment_for_routing(
    client: TestClient,
) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    token = make_workspace(client, "teacher")
    first_conversation = create_conversation(client, token)
    second_conversation = create_conversation(client, token)
    client.app.state.chat_provider = AttachmentAwareRouteClassifier()

    upload = client.post(
        f"/api/conversations/{first_conversation['id']}/attachments",
        files={"file": ("scores.csv", "匿名编号,章节,得分,满分\nA01,函数,72,100", "text/csv")},
        data={"scope": "workspace"},
        headers=auth(token),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{second_conversation['id']}/route",
        json={"content": "根据本节课目标，生成一份课堂练习"},
        headers=auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "lesson_design"
    assert body["selection_source"] == "llm_fallback"


def test_explicit_classroom_practice_intent_wins_over_learning_sheet(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    token = make_workspace(client, "teacher")
    conversation = create_conversation(client, token)
    client.app.state.chat_provider = FakeChatProvider(
        route_response='{"agent":"lesson_design","confidence":0.96,"reason":"当前指令要求生成课堂练习"}',
        deltas=("课堂练习",),
    )

    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={
            "file": (
                "learning_scores.csv",
                "匿名编号,课程,得分,满分\nSTUDENT_SECRET_001,Python,52,100",
                "text/csv",
            )
        },
        headers=auth(token),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "根据本节课目标，生成一份课堂练习。Python 数组"},
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    assert events["message_start"]["agent_id"] == "lesson_design"


def test_lesson_design_does_not_receive_learning_analysis_sheet_as_context(
    client: TestClient,
) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    token = make_workspace(client, "teacher")
    conversation = create_conversation(client, token)
    provider = FakeChatProvider(deltas=("课堂练习",))
    client.app.state.chat_provider = provider

    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={
            "file": (
                "learning_scores.csv",
                "匿名编号,课程,得分,满分\nSTUDENT_SECRET_001,Python,52,100",
                "text/csv",
            )
        },
        data={"scope": "workspace"},
        headers=auth(token),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={
            "content": "根据本节课目标生成课堂练习，Python 数组",
            "agent_id": "lesson_design",
        },
        headers=auth(token),
    )

    assert response.status_code == 200
    assert provider.calls
    serialized_prompt = json.dumps(provider.calls[-1], ensure_ascii=False)
    assert "STUDENT_SECRET_001" not in serialized_prompt
    assert "learning_scores.csv" not in serialized_prompt
