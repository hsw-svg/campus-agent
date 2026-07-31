import json
from collections.abc import AsyncIterator, Sequence
from uuid import uuid4

import pytest
from app.core.errors import AppError, TaskError

from app.agents.contracts import AgentContext, AgentRequest, ContextSource
from app.agents.admin.meeting_minutes import MeetingMinutesExecutor
from app.agents.admin.todo_breakdown import TodoBreakdownExecutor
from app.agents.executors.registry import AgentExecutorRegistry
from app.agents.p1_contracts import (
    CourseQAOutput,
    MeetingMinutesOutput,
    PersonalTutorOutput,
    ResumeAnalysisOutput,
    TodoBreakdownOutput,
)
from app.agents.specs import get_agent_spec
from app.agents.student.course_qa import CourseQAExecutor
from app.agents.student.personal_tutor import PersonalTutorExecutor
from app.agents.student.resume_helper import ResumeHelperExecutor


class FakeStructuredProvider:
    is_configured = True

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(
        self,
        messages: Sequence[dict[str, str]],
        *,
        response_format: dict | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield self.response


class FakeRetryStructuredProvider:
    is_configured = True

    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[list[dict[str, str]], dict | None]] = []

    async def stream_reply(
        self,
        messages: Sequence[dict[str, str]],
        *,
        response_format: dict | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append((list(messages), response_format))
        yield next(self.responses)


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
        ("student", "resume_helper"): "resume_helper",
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
    assert isinstance(registry.resolve("student", "resume_helper"), ResumeHelperExecutor)
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
    with pytest.raises(ValueError):
        ResumeAnalysisOutput.model_validate({"overall_summary": "只有摘要"})


@pytest.mark.asyncio
async def test_resume_executor_keeps_input_snapshot_and_renders_complete_draft() -> None:
    response = {
        "overall_summary": "需要聚焦。",
        "issues": [
            {
                "section": "经历",
                "severity": "high",
                "problem": "缺少细节",
                "evidence": "原文较短",
                "suggestion": "补充本人职责",
            }
        ],
        "section_suggestions": [
            {
                "section": "经历",
                "suggestions": ["按行动和结果组织"],
                "rewrite_examples": ["结果数据：待补充"],
            }
        ],
        "course_capability_matches": [],
        "job_match": {
            "matched_keywords": [],
            "gap_keywords": [],
            "guidance": "进行通用优化。",
        },
        "optimized_resume_sections": [
            {"heading": "个人概况", "markdown": "目标岗位：待补充"}
        ],
        "evidence_notice": "只使用已有证据。",
    }
    provider = FakeStructuredProvider(json.dumps(response, ensure_ascii=False))
    request = _request("student", "resume_helper")
    request = AgentRequest(
        **{
            **request.__dict__,
            "content": json.dumps(
                {
                    "resume_attachment_id": str(uuid4()),
                    "resume_filename": "resume.md",
                    "target_role": None,
                    "job_description": None,
                    "selected_courses": [],
                },
                ensure_ascii=False,
            ),
        }
    )

    result = await ResumeHelperExecutor(provider).execute(request)

    assert result.artifact is not None
    assert result.artifact.type == "resume_analysis"
    assert result.artifact.data["schema_version"] == "resume_analysis.v1"
    assert result.artifact.data["input"]["resume_filename"] == "resume.md"
    assert "# 优化后简历草稿" in result.text
    assert "待补充" in result.text


@pytest.mark.asyncio
async def test_resume_executor_retries_one_invalid_structured_response() -> None:
    valid_response = {
        "overall_summary": "需要聚焦。",
        "issues": [],
        "section_suggestions": [],
        "course_capability_matches": [],
        "job_match": {
            "matched_keywords": [],
            "gap_keywords": [],
            "guidance": "进行通用优化。",
        },
        "optimized_resume_sections": [
            {"heading": "个人概况", "markdown": "目标岗位：待补充"}
        ],
        "evidence_notice": "只使用已有证据。",
    }
    provider = FakeRetryStructuredProvider(
        [
            "以下是分析结果：\n```json\n{}\n```",
            json.dumps(valid_response, ensure_ascii=False),
        ]
    )
    request = _request("student", "resume_helper")
    request = AgentRequest(
        **{
            **request.__dict__,
            "content": json.dumps(
                {
                    "resume_attachment_id": str(uuid4()),
                    "resume_filename": "resume.pdf",
                    "target_role": None,
                    "job_description": None,
                    "selected_courses": [],
                },
                ensure_ascii=False,
            ),
        }
    )

    result = await ResumeHelperExecutor(provider).execute(request)

    assert result.artifact is not None
    assert len(provider.calls) == 2
    assert provider.calls[0][1] is None
    assert provider.calls[1][1] == {"type": "json_object"}
    retry_messages = provider.calls[1][0]
    assert retry_messages[-2]["role"] == "assistant"
    assert retry_messages[-1]["role"] == "user"
    assert "修正" in retry_messages[-1]["content"]


@pytest.mark.asyncio
async def test_resume_executor_stops_after_one_failed_correction() -> None:
    provider = FakeRetryStructuredProvider(["not-json", "still-not-json"])
    request = _request("student", "resume_helper")
    request = AgentRequest(
        **{
            **request.__dict__,
            "content": json.dumps(
                {
                    "resume_attachment_id": str(uuid4()),
                    "resume_filename": "resume.pdf",
                    "target_role": None,
                    "job_description": None,
                    "selected_courses": [],
                },
                ensure_ascii=False,
            ),
        }
    )

    with pytest.raises(TaskError, match="invalid_structured_output"):
        await ResumeHelperExecutor(provider).execute(request)

    assert len(provider.calls) == 2
    assert provider.calls[1][1] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_resume_executor_rejects_unselected_course_claims() -> None:
    response = {
        "overall_summary": "需要聚焦。",
        "issues": [],
        "section_suggestions": [],
        "course_capability_matches": [
            {
                "course_name": "未选择的课程",
                "progress_evidence": "无",
                "capability": "虚构能力",
                "suggested_wording": "不应出现",
            }
        ],
        "job_match": {
            "matched_keywords": [],
            "gap_keywords": [],
            "guidance": "通用建议",
        },
        "optimized_resume_sections": [
            {"heading": "个人概况", "markdown": "目标岗位：待补充"}
        ],
        "evidence_notice": "只使用已有证据。",
    }
    provider = FakeStructuredProvider(json.dumps(response, ensure_ascii=False))
    request = _request("student", "resume_helper")
    request = AgentRequest(
        **{
            **request.__dict__,
            "content": json.dumps(
                {
                    "resume_attachment_id": str(uuid4()),
                    "resume_filename": "resume.md",
                    "target_role": None,
                    "job_description": None,
                    "selected_courses": [],
                },
                ensure_ascii=False,
            ),
        }
    )

    with pytest.raises(AppError, match="resume_analysis_evidence_invalid"):
        await ResumeHelperExecutor(provider).execute(request)
