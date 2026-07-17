import json
from collections.abc import AsyncIterator, Sequence
from uuid import uuid4

import pytest
from app.core.errors import TaskError

from app.agents.contracts import AgentContext, AgentRequest, ContextSource
from app.agents.admin.meeting_minutes import MeetingMinutesExecutor
from app.agents.admin.todo_breakdown import TodoBreakdownExecutor
from app.agents.executors.registry import AgentExecutorRegistry
from app.agents.p1_contracts import (
    CourseQAOutput,
    MeetingMinutesOutput,
    PersonalTutorOutput,
    TodoBreakdownOutput,
)
from app.agents.specs import get_agent_spec
from app.agents.student.course_qa import CourseQAExecutor
from app.agents.student.personal_tutor import PersonalTutorExecutor


class FakeStructuredProvider:
    is_configured = True

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(
        self, messages: Sequence[dict[str, str]]
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield self.response


def _request(role: str, agent_id: str) -> AgentRequest:
    return AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role=role,
        agent_id=agent_id,
        content="请根据材料处理当前任务",
        context=AgentContext(
            messages=({"role": "system", "content": "existing context"},),
            sources=(
                ContextSource(
                    attachment_id=uuid4(),
                    filename="selected.md",
                    excerpt="当前选中的材料片段",
                ),
            ),
        ),
    )


def test_p1_specs_have_dedicated_executors_and_context_boundaries() -> None:
    expected = {
        ("student", "course_qa"): "course_qa",
        ("student", "personal_tutor"): "personal_tutor",
        ("admin", "meeting_minutes"): "meeting_minutes",
        ("admin", "todo_breakdown"): "todo_breakdown",
    }

    for (role, agent_id), executor_id in expected.items():
        spec = get_agent_spec(role, agent_id)
        assert spec is not None
        assert spec.executor_id == executor_id
        assert spec.system_prompt != "你是校园智能助手。只使用当前角色允许的任务，并明确说明资料不足。"
        assert spec.context_policy.exclude_learning_details is True
        assert spec.context_policy.allow_implicit_conversation_attachments is False

    student_course_spec = get_agent_spec("student", "course_qa")
    assert student_course_spec is not None
    assert student_course_spec.context_policy.requires_explicit_attachments is True

    admin_minutes_spec = get_agent_spec("admin", "meeting_minutes")
    assert admin_minutes_spec is not None
    assert admin_minutes_spec.context_policy.requires_explicit_attachments is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "agent_id", "response", "executor_type", "artifact_type"),
    [
        (
            "student",
            "course_qa",
            {
                "answer": "切片会返回新的序列。",
                "key_points": ["切片包含起点和终点"],
                "follow_up_questions": ["要继续看步长吗？"],
            },
            CourseQAExecutor,
            "course_qa",
        ),
        (
            "student",
            "personal_tutor",
            {
                "diagnosis": "混淆了索引与切片。",
                "explanation": "索引返回单个元素，切片返回序列。",
                "mistakes": ["忽略了冒号"],
                "practice": ["比较 a[0] 与 a[0:1]"],
                "follow_up_questions": ["需要一道变式题吗？"],
            },
            PersonalTutorExecutor,
            "personal_tutor",
        ),
        (
            "admin",
            "meeting_minutes",
            {
                "topics": ["项目进度"],
                "decisions": [
                    {
                        "decision": "下周复盘",
                        "owner": "李老师",
                        "due_date": "2026-07-24",
                        "evidence": "会议明确约定",
                    }
                ],
                "action_items": [
                    {"task": "整理复盘材料", "owner": None, "due_date": None, "evidence": None}
                ],
            },
            MeetingMinutesExecutor,
            "meeting_minutes",
        ),
        (
            "admin",
            "todo_breakdown",
            {
                "items": [
                    {
                        "task": "发送会议纪要",
                        "owner": "王老师",
                        "due_date": "2026-07-18",
                        "priority": "高",
                        "evidence": "会议行动项",
                    }
                ]
            },
            TodoBreakdownExecutor,
            "todo_breakdown",
        ),
    ],
)
async def test_p1_executors_parse_structured_output_and_keep_context_citations(
    role: str,
    agent_id: str,
    response: dict,
    executor_type: type,
    artifact_type: str,
) -> None:
    provider = FakeStructuredProvider(json.dumps(response, ensure_ascii=False))
    result = await executor_type(provider).execute(_request(role, agent_id))

    assert result.artifact is not None
    assert result.artifact.type == artifact_type
    assert result.structured_data == response
    assert result.artifact.data == response
    assert result.citations[0].filename == "selected.md"
    assert result.validation == {
        "valid": True,
        "schema": f"{agent_id}.v1",
        "source_count": 1,
    }
    assert result.text.startswith("# ")
    assert provider.calls
    assert "JSON" in provider.calls[0][0]["content"]


def test_p1_registry_does_not_fall_back_to_generic_chat() -> None:
    provider = FakeStructuredProvider("{}")
    registry = AgentExecutorRegistry(provider)

    assert isinstance(registry.resolve("student", "course_qa"), CourseQAExecutor)
    assert isinstance(registry.resolve("student", "personal_tutor"), PersonalTutorExecutor)
    assert isinstance(registry.resolve("admin", "meeting_minutes"), MeetingMinutesExecutor)
    assert isinstance(registry.resolve("admin", "todo_breakdown"), TodoBreakdownExecutor)


@pytest.mark.asyncio
async def test_invalid_p1_json_is_a_typed_error() -> None:
    provider = FakeStructuredProvider("not-json")

    with pytest.raises(TaskError, match="invalid_structured_output"):
        await CourseQAExecutor(provider).execute(_request("student", "course_qa"))


def test_p1_output_models_reject_missing_required_fields() -> None:
    with pytest.raises(ValueError):
        CourseQAOutput.model_validate({"answer": "只有回答"})
    with pytest.raises(ValueError):
        PersonalTutorOutput.model_validate({"diagnosis": "只有诊断"})
    with pytest.raises(ValueError):
        MeetingMinutesOutput.model_validate({"topics": ["议题"]})
    with pytest.raises(ValueError):
        TodoBreakdownOutput.model_validate({"items": [{"owner": "没有任务"}]})
