import json
from collections.abc import AsyncIterator, Sequence

from fastapi.testclient import TestClient

from app.agents.workflows import TEACHER_STANDALONE_AGENT_WORKFLOW_ID
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


class FakeChatProvider:
    is_configured = True

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield self.response


ACTIVITY_JSON = json.dumps(
    {
        "topic": "函数极限",
        "objectives": ["理解极限的直观含义"],
        "activities": [
            {
                "type": "discussion",
                "title": "情境讨论",
                "duration_minutes": 12,
                "prompt": "用生活情境解释无限接近。",
                "rubric": [{"criterion": "能说明接近但不必到达", "points": 2}],
            }
        ],
    },
    ensure_ascii=False,
)


def stream(
    client: TestClient,
    conversation_id: str,
    token: str,
    *,
    agent_id: str,
    content: str,
) -> list[tuple[str, dict]]:
    response = client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={
            "content": content,
            "agent_id": agent_id,
            "selected_attachment_ids": [],
            "workflow_id": TEACHER_STANDALONE_AGENT_WORKFLOW_ID,
        },
        headers=auth(token),
    )
    assert response.status_code == 200
    return events_from_stream(response.text)


def test_standalone_activity_package_runs_without_materials(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    provider = FakeChatProvider(ACTIVITY_JSON)
    client.app.state.chat_provider = provider

    events = stream(
        client,
        conversation["id"],
        token,
        agent_id="classroom_interaction",
        content="生成课堂互动活动包：教学主题是函数极限，教学目标：理解极限的直观含义，总时长 45 分钟",
    )

    artifact = next(data for name, data in events if name == "artifact")
    assert artifact["type"] == "classroom_activity_package"
    assert provider.calls


def test_standalone_course_iteration_runs_without_materials(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    provider = FakeChatProvider("建议先用直观图像引入，再逐步过渡到形式化定义。")
    client.app.state.chat_provider = provider

    events = stream(
        client,
        conversation["id"],
        token,
        agent_id="course_iteration",
        content="课程迭代：教学主题是函数极限，迭代目标是增强直观理解。",
    )

    assert any(name == "done" for name, _ in events)
    assert not any(name == "error" for name, _ in events)
    assert provider.calls


def test_standalone_learning_analysis_still_requires_table(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    provider = FakeChatProvider("不应调用模型")
    client.app.state.chat_provider = provider

    events = stream(
        client,
        conversation["id"],
        token,
        agent_id="learning_analysis",
        content="分析学情",
    )

    error = next(data for name, data in events if name == "error")
    assert error["code"] == "agent_input_incomplete"
    assert provider.calls == []

def test_course_conversation_cannot_use_standalone_empty_material_exception(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    course = client.post("/api/courses", json={"name": "高等数学"}, headers=auth(token)).json()
    conversation = client.post(
        "/api/conversations",
        json={"course_id": course["id"]},
        headers=auth(token),
    ).json()
    provider = FakeChatProvider(ACTIVITY_JSON)
    client.app.state.chat_provider = provider

    activity_events = stream(
        client,
        conversation["id"],
        token,
        agent_id="classroom_interaction",
        content="生成课堂互动活动包：教学主题是函数极限，教学目标：理解极限的直观含义，总时长 45 分钟",
    )
    activity_error = next(data for name, data in activity_events if name == "error")
    assert activity_error["code"] == "classroom_activity_input_incomplete"

    iteration_events = stream(
        client,
        conversation["id"],
        token,
        agent_id="course_iteration",
        content="课程迭代：教学主题是函数极限，迭代目标是增强直观理解。",
    )
    iteration_error = next(data for name, data in iteration_events if name == "error")
    assert iteration_error["code"] == "agent_input_incomplete"
    assert provider.calls == []
