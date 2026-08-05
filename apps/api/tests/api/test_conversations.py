import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.contracts import AgentRequest, AgentResult
from app.services.conversations import _stream_executor
from tests.api.conftest import make_workspace


class FakeChatProvider:
    """A configured provider that streams a fixed reply for deterministic tests."""

    def __init__(self, deltas: Sequence[str]) -> None:
        self.deltas = list(deltas)
        self.calls: list[list[dict[str, str]]] = []

    @property
    def is_configured(self) -> bool:
        return True

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        for delta in self.deltas:
            yield delta


class FailingChatProvider:
    @property
    def is_configured(self) -> bool:
        return True

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        if False:  # pragma: no cover - makes this an async generator
            yield ""
        raise RuntimeError("upstream timeout")


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def create_conversation(client: TestClient, token: str, agent_id: str | None = None) -> dict:
    response = client.post("/api/conversations", json={"agent_id": agent_id}, headers=auth(token))
    assert response.status_code == 201
    return response.json()


def read_events(text: str) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_line, data_line = block.split("\n", 1)
        events.append((event_line.removeprefix("event: "), data_line.removeprefix("data: ")))
    return events


def test_new_conversation_starts_empty(client: TestClient) -> None:
    token = make_workspace(client, "student")
    conversation = create_conversation(client, token)

    assert conversation["title"] == "新对话"
    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=auth(token)
    )
    assert messages.status_code == 200
    assert messages.json() == []


def test_streaming_reply_emits_protocol_events_and_persists_turns(client: TestClient) -> None:
    token = make_workspace(client, "student")
    client.app.state.chat_provider = FakeChatProvider(["你好", "，世界"])
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "介绍一下你自己"},
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    types = [event_type for event_type, _ in events]
    assert types[0] == "message_start"
    assert types[-1] == "done"
    assert "delta" in types

    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=auth(token)
    ).json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "你好，世界"


def test_streaming_reply_forwards_each_visible_model_delta(client: TestClient) -> None:
    token = make_workspace(client, "student")
    client.app.state.chat_provider = FakeChatProvider(["第", "一", "步"])
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "请分步回答"},
        headers=auth(token),
    )

    assert response.status_code == 200
    events = read_events(response.text)
    deltas = [json.loads(data)["text"] for name, data in events if name == "delta"]
    statuses = [json.loads(data) for name, data in events if name == "tool_status"]
    assert deltas == ["第", "一", "步"]
    assert any(status["phase"] == "model" and status["state"] == "active" for status in statuses)
    assert any(status["phase"] == "model" and status["state"] == "completed" for status in statuses)


def test_first_user_turn_becomes_the_conversation_title(client: TestClient) -> None:
    token = make_workspace(client, "student")
    client.app.state.chat_provider = FakeChatProvider(["好的"])
    conversation = create_conversation(client, token)

    client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "帮我复习线性代数"},
        headers=auth(token),
    )

    refreshed = client.get(
        f"/api/conversations/{conversation['id']}", headers=auth(token)
    ).json()
    assert refreshed["title"] == "帮我复习线性代数"


def test_unconfigured_model_emits_a_retryable_error_and_keeps_the_user_turn(
    client: TestClient,
) -> None:
    token = make_workspace(client, "student")
    # The default provider from create_app is unconfigured in tests.
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "在吗"},
        headers=auth(token),
    )

    events = dict(read_events(response.text))
    assert "error" in events
    assert '"retryable": true' in events["error"]

    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=auth(token)
    ).json()
    assert [message["role"] for message in messages] == ["user"]


def test_model_failure_surfaces_as_stream_error_without_assistant_message(
    client: TestClient,
) -> None:
    token = make_workspace(client, "student")
    client.app.state.chat_provider = FailingChatProvider()
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "生成练习题"},
        headers=auth(token),
    )

    events = dict(read_events(response.text))
    assert "error" in events
    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=auth(token)
    ).json()
    assert [message["role"] for message in messages] == ["user"]


def test_legacy_executor_emits_cancellable_heartbeats() -> None:
    class LegacyExecutor:
        async def execute(self, request: AgentRequest) -> AgentResult:
            await asyncio.sleep(0.75)
            return AgentResult(text="完成")

    request = AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role="teacher",
        agent_id="legacy",
        content="生成教学建议",
    )

    events = asyncio.run(_collect_executor_events(LegacyExecutor(), request))

    statuses = [event.progress for event in events if event.type == "status"]
    assert statuses[0] is not None and statuses[0].state == "active"
    assert any(status is not None and status.count is not None for status in statuses)
    assert statuses[-1] is not None and statuses[-1].state == "completed"
    assert events[-1].result is not None and events[-1].result.text == "完成"


@pytest.mark.asyncio
async def test_legacy_executor_cancellation_cleans_up_background_task() -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class LegacyExecutor:
        async def execute(self, request: AgentRequest) -> AgentResult:
            started.set()
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return AgentResult(text="不会到达")

    request = AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role="teacher",
        agent_id="legacy",
        content="生成教学建议",
    )
    stream = _stream_executor(LegacyExecutor(), request)
    first_event = await anext(stream)
    assert first_event.type == "status"

    pending_event = asyncio.create_task(anext(stream))
    await started.wait()
    pending_event.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending_event
    assert cancelled.is_set()


async def _collect_executor_events(executor: object, request: AgentRequest) -> list:
    return [event async for event in _stream_executor(executor, request)]
