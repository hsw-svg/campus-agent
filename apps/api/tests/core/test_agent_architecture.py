from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.agents.contracts import AgentContext, AgentRequest
from app.agents.executors.classroom_interaction import ClassroomInteractionExecutor
from app.agents.executors.lesson_design import LessonDesignExecutor
from app.agents.executors.registry import AgentExecutorRegistry
from app.agents.specs import get_agent_spec
from app.integrations.llm.providers import ChatProvider
from app.skills.classroom_observation import ClassroomObservationSkill


class FakeProvider:
    is_configured = True

    async def stream_reply(self, messages) -> AsyncIterator[str]:
        assert any("统计" in message["content"] for message in messages)
        yield "根据班级统计，先复习列表切片。"


def _request(agent_id: str, content: str) -> AgentRequest:
    return AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role="teacher",
        agent_id=agent_id,
        content=content,
        context=AgentContext(messages=({"role": "system", "content": "test"},)),
    )


def test_observation_skill_computes_class_ratios() -> None:
    result = ClassroomObservationSkill().run("这道题 8 人选 A、21 人选 B、5 人选 C")

    assert result.total == 34
    assert result.counts == {"A": 8, "B": 21, "C": 5}
    assert result.ratios["B"] == 0.6176


@pytest.mark.asyncio
async def test_executor_registry_resolves_independent_teacher_executors() -> None:
    provider = FakeProvider()
    registry = AgentExecutorRegistry(provider)  # type: ignore[arg-type]

    lesson = registry.resolve(get_agent_spec("teacher", "lesson_design"))
    classroom = registry.resolve(get_agent_spec("teacher", "classroom_interaction"))

    assert isinstance(lesson, LessonDesignExecutor)
    assert isinstance(classroom, ClassroomInteractionExecutor)


@pytest.mark.asyncio
async def test_classroom_executor_keeps_program_computed_statistics() -> None:
    result = await ClassroomInteractionExecutor(FakeProvider()).execute(
        _request("classroom_interaction", "这道题 8 人选 A、21 人选 B、5 人选 C")
    )

    assert result.structured_data == {
        "scope": "class",
        "counts": {"A": 8, "B": 21, "C": 5},
        "total": 34,
        "ratios": {"A": 0.2353, "B": 0.6176, "C": 0.1471},
    }
