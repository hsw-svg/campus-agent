"""Structured contracts and deterministic renderers for the first P1 agents."""

from typing import Annotated, Literal

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


class ResumeIssue(_StructuredOutput):
    section: NonEmptyText
    severity: Literal["high", "medium", "low"]
    problem: NonEmptyText
    evidence: NonEmptyText
    suggestion: NonEmptyText


class ResumeSectionSuggestion(_StructuredOutput):
    section: NonEmptyText
    suggestions: list[NonEmptyText]
    rewrite_examples: list[NonEmptyText]


class CourseCapabilityMatch(_StructuredOutput):
    course_name: NonEmptyText
    progress_evidence: NonEmptyText
    capability: NonEmptyText
    suggested_wording: NonEmptyText


class ResumeJobMatch(_StructuredOutput):
    matched_keywords: list[NonEmptyText]
    gap_keywords: list[NonEmptyText]
    guidance: NonEmptyText


class OptimizedResumeSection(_StructuredOutput):
    heading: NonEmptyText
    markdown: NonEmptyText


class ResumeAnalysisOutput(_StructuredOutput):
    overall_summary: NonEmptyText
    issues: list[ResumeIssue]
    section_suggestions: list[ResumeSectionSuggestion]
    course_capability_matches: list[CourseCapabilityMatch]
    job_match: ResumeJobMatch
    optimized_resume_sections: list[OptimizedResumeSection]
    evidence_notice: NonEmptyText


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


def resume_analysis_markdown(output: ResumeAnalysisOutput) -> str:
    issue_lines = [
        (
            f"**{item.section} · {_severity_label(item.severity)}**：{item.problem}\n"
            f"  - 依据：{item.evidence}\n"
            f"  - 建议：{item.suggestion}"
        )
        for item in output.issues
    ]
    suggestion_sections = []
    for item in output.section_suggestions:
        suggestion_sections.extend(
            (
                f"### {item.section}",
                "",
                "建议：",
                _bullet_list(item.suggestions),
                "",
                "改写示例：",
                _bullet_list(item.rewrite_examples),
                "",
            )
        )
    course_lines = [
        (
            f"**{item.course_name}**：{item.capability}\n"
            f"  - 学习依据：{item.progress_evidence}\n"
            f"  - 推荐表述：{item.suggested_wording}"
        )
        for item in output.course_capability_matches
    ]
    draft_sections: list[str] = []
    for item in output.optimized_resume_sections:
        draft_sections.extend((f"## {item.heading}", "", item.markdown, ""))
    return "\n".join(
        (
            "# 简历优化报告",
            "",
            "## 总体诊断",
            output.overall_summary,
            "",
            "## 问题清单",
            _bullet_list(issue_lines),
            "",
            "## 分模块修改建议",
            *suggestion_sections,
            "## 课程能力匹配",
            _bullet_list(course_lines),
            "",
            "## 岗位关键词匹配",
            "### 已匹配关键词",
            _bullet_list(output.job_match.matched_keywords),
            "",
            "### 待补足关键词",
            _bullet_list(output.job_match.gap_keywords),
            "",
            output.job_match.guidance,
            "",
            "# 优化后简历草稿",
            "",
            *draft_sections,
            "## 证据说明",
            output.evidence_notice,
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


def _severity_label(value: Literal["high", "medium", "low"]) -> str:
    return {"high": "高优先级", "medium": "中优先级", "low": "低优先级"}[value]
