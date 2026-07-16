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
        "topic": "Python 列表",
        "objectives": ["区分索引和切片"],
        "activities": [
            {
                "type": "multiple_choice",
                "title": "快速诊断",
                "duration_minutes": 5,
                "prompt": "下列哪项是切片？",
                "options": ["A. a[0]", "B. a[1:3]"],
                "answer": "B",
                "explanation": "切片返回一个序列。",
                "common_misconceptions": ["把索引和切片混淆"],
                "teacher_prompt": "请说明方括号中的范围。",
                "differentiated_hints": {"support": "先观察是否有冒号"},
                "branches": [{"condition": "多数选择 A", "action": "回到索引示例"}],
            },
            {
                "type": "discussion",
                "title": "同伴解释",
                "duration_minutes": 8,
                "prompt": "解释索引和切片的区别。",
                "rubric": [{"criterion": "指出返回结果差异", "points": 2}],
            },
        ],
    },
    ensure_ascii=False,
)


SUMMARY_JSON = json.dumps(
    {
        "classroom_summary": "多数学生能识别切片语法，但仍需加强结果类型解释。",
        "common_misconceptions": ["把索引结果和切片结果混为一谈"],
        "teaching_reflection": "先统计再追问能更快定位共同误区。",
        "follow_up_practice": ["比较 a[0] 与 a[1:3] 的返回结果"],
        "next_lesson_adjustments": ["增加一个边界索引和空切片案例"],
    },
    ensure_ascii=False,
)


def stream(client: TestClient, conversation_id: str, token: str, content: str, **extra: object):
    payload = {"content": content, "agent_id": "classroom_interaction", **extra}
    return client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json=payload,
        headers=auth(token),
    )


def test_stage7_activity_observation_summary_and_csv_export(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    material = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("python-list.md", "Python 列表索引和切片课程资料", "text/markdown")},
        headers=auth(token),
    )
    assert material.status_code == 201
    material_id = material.json()["id"]
    client.app.state.chat_provider = FakeChatProvider(ACTIVITY_JSON)

    activity_response = stream(
        client,
        conversation["id"],
        token,
        "生成课堂互动活动包：教学主题是 Python 列表，教学目标：区分索引和切片，总时长 45 分钟",
        selected_attachment_ids=[material_id],
    )
    assert activity_response.status_code == 200
    activity_event = next(
        data for name, data in events_from_stream(activity_response.text)
        if name == "artifact" and data.get("type") == "classroom_activity_package"
    )
    activity_id = activity_event["artifact_id"]
    assert activity_event["data"]["total_minutes"] == 13
    assert activity_event["data"]["validation"]["valid"] is True

    client.app.state.chat_provider = FakeChatProvider("先复习切片，再追问返回值类型。")
    observation_response = stream(
        client,
        conversation["id"],
        token,
        "这道题 8 人选 A、21 人选 B、5 人选 C，大部分学生解释不清索引与切片",
    )
    observation_event = next(
        data for name, data in events_from_stream(observation_response.text)
        if name == "artifact" and data.get("type") == "classroom_observation"
    )
    observation_id = observation_event["artifact_id"]
    assert observation_event["data"]["total"] == 34
    assert observation_event["data"]["ratios"]["B"] == 0.6176

    listed = client.get(
        f"/api/conversations/{conversation['id']}/artifacts",
        headers=auth(token),
    )
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} >= {activity_id, observation_id}

    client.app.state.chat_provider = FakeChatProvider(SUMMARY_JSON)
    summary_response = stream(
        client,
        conversation["id"],
        token,
        "生成课后总结",
        selected_artifact_ids=[activity_id, observation_id],
    )
    summary_event = next(
        data for name, data in events_from_stream(summary_response.text)
        if name == "artifact" and data.get("type") == "classroom_summary"
    )
    assert summary_event["data"]["common_misconceptions"]

    exported = client.get(
        f"/api/artifacts/{summary_event['artifact_id']}/export?format=csv",
        headers=auth(token),
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "classroom_summary" in exported.text


def test_stage7_ambiguous_observation_stays_pending_confirmation(client: TestClient) -> None:
    token = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(token)).json()
    provider = FakeChatProvider("不应调用模型")
    client.app.state.chat_provider = provider

    response = stream(
        client,
        conversation["id"],
        token,
        "第1题 8 人选 A、21 人选 B；第2题 8 人选 A、5 人选 C",
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    artifact = next(data for name, data in events if name == "artifact")
    assert artifact["data"]["status"] == "needs_confirmation"
    assert any(name == "done" for name, _ in events)
    assert provider.calls == []
