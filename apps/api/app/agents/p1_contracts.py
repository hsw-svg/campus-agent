"""Structured contracts and deterministic renderers for the first P1 agents."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


NonEmptyText = Annotated[str, Field(min_length=1)]


class _StructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourseQAOutput(_StructuredOutput):
    answer: NonEmptyText
    key_points: list[NonEmptyText]
    follow_up_questions: list[NonEmptyText]


class PersonalTutorOutput(_StructuredOutput):
    diagnosis: NonEmptyText
    explanation: NonEmptyText
    mistakes: list[NonEmptyText]
    practice: list[NonEmptyText]
    follow_up_questions: list[NonEmptyText]


class Decision(_StructuredOutput):
    decision: NonEmptyText
    owner: str | None = None
    due_date: str | None = None
    evidence: str | None = None

    @field_validator("owner", "due_date", "evidence", mode="before")
    @classmethod
    def empty_optional_text_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class ActionItem(_StructuredOutput):
    task: NonEmptyText
    owner: str | None = None
    due_date: str | None = None
    evidence: str | None = None

    @field_validator("owner", "due_date", "evidence", mode="before")
    @classmethod
    def empty_optional_text_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class MeetingMinutesOutput(_StructuredOutput):
    topics: list[NonEmptyText]
    decisions: list[Decision]
    action_items: list[ActionItem]


class TodoItem(_StructuredOutput):
    task: NonEmptyText
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    evidence: str | None = None

    @field_validator("owner", "due_date", "priority", "evidence", mode="before")
    @classmethod
    def empty_optional_text_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class TodoBreakdownOutput(_StructuredOutput):
    items: list[TodoItem]


def course_qa_markdown(output: CourseQAOutput) -> str:
    return "\n".join(
        (
            "# 课程资料问答",
            "",
            "## 回答",
            output.answer,
            "",
            "## 要点",
            _bullet_list(output.key_points),
            "",
            "## 追问",
            _bullet_list(output.follow_up_questions),
        )
    )


def personal_tutor_markdown(output: PersonalTutorOutput) -> str:
    return "\n".join(
        (
            "# 个性化答疑",
            "",
            "## 诊断",
            output.diagnosis,
            "",
            "## 讲解",
            output.explanation,
            "",
            "## 易错点",
            _bullet_list(output.mistakes),
            "",
            "## 练习建议",
            _bullet_list(output.practice),
            "",
            "## 追问",
            _bullet_list(output.follow_up_questions),
        )
    )


def meeting_minutes_markdown(output: MeetingMinutesOutput) -> str:
    decisions = [
        _with_metadata(item.decision, item.owner, item.due_date, item.evidence)
        for item in output.decisions
    ]
    action_items = [
        _with_metadata(item.task, item.owner, item.due_date, item.evidence)
        for item in output.action_items
    ]
    return "\n".join(
        (
            "# 会议纪要",
            "",
            "## 议题",
            _bullet_list(output.topics),
            "",
            "## 决议",
            _bullet_list(decisions),
            "",
            "## 行动项",
            _bullet_list(action_items),
        )
    )


def todo_breakdown_markdown(output: TodoBreakdownOutput) -> str:
    items = [
        _with_metadata(item.task, item.owner, item.due_date, item.evidence, item.priority)
        for item in output.items
    ]
    return "\n".join(
        (
            "# 待办拆解",
            "",
            "## 待办项",
            _bullet_list(items),
        )
    )


def _bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- 暂无"


def _with_metadata(
    value: str,
    owner: str | None,
    due_date: str | None,
    evidence: str | None,
    priority: str | None = None,
) -> str:
    metadata = []
    if owner:
        metadata.append(f"负责人：{owner}")
    if due_date:
        metadata.append(f"截止：{due_date}")
    if priority:
        metadata.append(f"优先级：{priority}")
    if evidence:
        metadata.append(f"依据：{evidence}")
    return f"{value}（{'；'.join(metadata)}）" if metadata else value
