"""Role-scoped routing decisions for the conversation service.

The router is deliberately separate from agent execution.  It only chooses a
whitelisted agent and reports why that choice was made; the selected agent (or
the shared chat service during this stage) remains responsible for producing a
business result.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.agents.registry import AgentDefinition, is_agent_available_for_role, list_agents
from app.core.errors import AppError, TaskError
from app.core.json_guard import parse_json

ROUTE_CONFIDENCE_THRESHOLD = 0.8


class RouteClassifier(Protocol):
    @property
    def is_configured(self) -> bool: ...

    async def classify_route(self, messages: list[dict[str, str]]) -> str: ...


@dataclass(frozen=True)
class RouteAttachment:
    """The attachment facts exposed to classification, never the raw file."""

    filename: str
    content_type: str
    headers: tuple[str, ...] = ()
    text_excerpt: str = ""
    status: str | None = None


@dataclass(frozen=True)
class RouteContext:
    role: str
    content: str
    attachments: tuple[RouteAttachment, ...] = ()
    workspace_attachments: tuple[RouteAttachment, ...] = ()
    selected_attachment_ids: tuple[str, ...] = ()
    recent_messages: tuple[dict[str, Any], ...] = ()
    conversation_agent_id: str | None = None


@dataclass(frozen=True)
class RouteDecision:
    agent: str | None
    confidence: float
    reason: str
    missing_inputs: tuple[str, ...] = ()
    selection_source: str = "rule"
    candidates: tuple[str, ...] = ()
    requires_confirmation: bool = False


class LLMRouteOutput(BaseModel):
    agent: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=1000)
    missing_inputs: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class _RuleMatch:
    agent: str
    score: int
    reason: str


class AgentRouter:
    """Choose an agent using deterministic evidence, then structured LLM output."""

    def __init__(
        self,
        classifier: RouteClassifier | None = None,
        confidence_threshold: float = ROUTE_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.classifier = classifier
        self.confidence_threshold = confidence_threshold

    async def route(
        self,
        context: RouteContext,
        manual_agent_id: str | None = None,
    ) -> RouteDecision:
        available = list_agents(context.role)
        if not available:
            raise AppError(
                code="role_not_supported",
                message="No agents are registered for this role.",
                status_code=400,
            )

        if manual_agent_id is not None:
            self._ensure_agent_available(context.role, manual_agent_id)
            missing = _missing_inputs_for_agent(manual_agent_id, context)
            return RouteDecision(
                agent=manual_agent_id,
                confidence=1.0,
                reason="用户手动选择了该智能体。",
                missing_inputs=tuple(missing),
                selection_source="manual",
                candidates=(manual_agent_id,),
            )

        rule_match = _match_rules(context, {agent.id for agent in available})
        if rule_match is not None:
            confidence = _rule_confidence(rule_match.score)
            if confidence >= self.confidence_threshold:
                return RouteDecision(
                    agent=rule_match.agent,
                    confidence=confidence,
                    reason=rule_match.reason,
                    missing_inputs=tuple(_missing_inputs_for_agent(rule_match.agent, context)),
                    selection_source="rule",
                    candidates=(rule_match.agent,),
                )

        if self._can_classify():
            try:
                raw = await self.classifier.classify_route(  # type: ignore[union-attr]
                    _classifier_messages(context, available)
                )
                llm_result = parse_json(raw, LLMRouteOutput)
            except TaskError:
                # An invalid classifier response must never become an agent
                # invocation.  Let the user choose from the safe whitelist.
                return self._confirmation_decision(
                    available,
                    rule_match,
                    "自动识别结果不可用，请确认要调用的智能体。",
                    source="llm",
                )
            except Exception:
                return self._confirmation_decision(
                    available,
                    rule_match,
                    "自动识别服务暂时不可用，请确认要调用的智能体。",
                    source="llm",
                )

            if llm_result.agent is not None:
                self._ensure_agent_available(context.role, llm_result.agent)
                candidates = (llm_result.agent,)
            else:
                candidates = _candidate_ids(available, rule_match)
            requires_confirmation = (
                llm_result.agent is None
                or llm_result.confidence < self.confidence_threshold
            )
            return RouteDecision(
                agent=llm_result.agent if not requires_confirmation else None,
                confidence=llm_result.confidence,
                reason=llm_result.reason,
                missing_inputs=tuple(llm_result.missing_inputs),
                selection_source="llm",
                candidates=candidates,
                requires_confirmation=requires_confirmation,
            )

        # This compatibility path is used while no classifier is configured.
        # The conversation can still use the shared chat provider, but no
        # guessed specialist is invoked.
        if rule_match is not None:
            candidates = (rule_match.agent,)
            reason = rule_match.reason
        else:
            candidates = _candidate_ids(available, None)
            reason = "暂时无法确定最合适的智能体。"
        return RouteDecision(
            agent=None,
            confidence=_rule_confidence(rule_match.score) if rule_match else 0.0,
            reason=reason,
            selection_source="fallback",
            candidates=candidates,
            requires_confirmation=False,
        )

    def _can_classify(self) -> bool:
        return bool(
            self.classifier
            and getattr(self.classifier, "is_configured", False)
            and callable(getattr(self.classifier, "classify_route", None))
        )

    @staticmethod
    def _ensure_agent_available(role: str, agent_id: str) -> None:
        if not is_agent_available_for_role(role, agent_id):
            raise AppError(
                code="agent_not_available",
                message="The requested agent is not available for this role.",
                status_code=400,
                details={"role": role, "agent_id": agent_id},
            )

    @staticmethod
    def _confirmation_decision(
        available: tuple[AgentDefinition, ...],
        rule_match: _RuleMatch | None,
        reason: str,
        *,
        source: str,
    ) -> RouteDecision:
        return RouteDecision(
            agent=None,
            confidence=_rule_confidence(rule_match.score) if rule_match else 0.0,
            reason=reason,
            selection_source=source,
            candidates=_candidate_ids(available, rule_match),
            requires_confirmation=True,
        )


def _match_rules(context: RouteContext, available: set[str]) -> _RuleMatch | None:
    content = context.content.lower()
    attachment_text = "\n".join(
        " ".join(
            (
                attachment.filename,
                attachment.content_type,
                *attachment.headers,
                attachment.text_excerpt[:1200],
            )
        ).lower()
        for attachment in context.attachments
    )
    recent_text = "\n".join(
        str(message.get("content", "")) for message in context.recent_messages
    )
    all_text = f"{content}\n{attachment_text}"
    if _is_short_follow_up(content):
        all_text = f"{all_text}\n{recent_text}"
    scores: dict[str, tuple[int, list[str]]] = {}

    def add(agent: str, amount: int, evidence: str) -> None:
        if agent not in available:
            return
        score, reasons = scores.get(agent, (0, []))
        scores[agent] = (score + amount, [*reasons, evidence])

    # Explicit production requests describe the desired output and must take
    # precedence over incidental evidence in a workspace attachment.  A
    # teacher may keep a learning sheet in the workspace while asking for a
    # classroom exercise; that request is lesson design, not analysis.
    explicit_lesson_design = any(
        term in content for term in ("课堂练习", "练习题", "课堂题", "教案", "教学设计")
    )
    add("lesson_design", 6, "任务明确要求生成课堂练习或教学设计") if explicit_lesson_design else None

    explicit_learning_analysis = any(
        term in content for term in ("分析学情", "学情分析", "研判学情", "分析成绩表")
    )
    add("learning_analysis", 6, "任务明确要求进行班级整体学情分析") if explicit_learning_analysis else None

    explicit_classroom_interaction = any(
        term in content
        for term in (
            "课堂互动",
            "活动包",
            "课堂观察",
            "课堂总结",
            "课后总结",
            "人选",
        )
    )
    add("classroom_interaction", 6, "任务明确要求生成或分析课堂互动成果") if explicit_classroom_interaction else None

    tabular = any(_is_tabular(attachment) for attachment in context.attachments)
    grade_terms = ("成绩", "得分", "分数", "满分", "正确率", "匿名编号", "student_no", "score")
    grade_headers = sum(term in attachment_text for term in grade_terms)
    neutral_message = _is_neutral_message(content)
    if not explicit_lesson_design and not explicit_learning_analysis and not neutral_message:
        if tabular:
            add("learning_analysis", 2, "附件是 CSV/XLSX 等表格")
        if grade_headers >= 2:
            add("learning_analysis", 4, "附件表头包含成绩分析字段")
        if any(term in all_text for term in grade_terms):
            add("learning_analysis", 2, "任务包含成绩或得分关键词")

    if any(term in all_text for term in ("简历", "resume", "cv", "求职")):
        add("resume_helper", 3, "任务或附件指向简历")
    resume_terms = ("项目经历", "教育背景", "工作经历", "技能", "自我介绍", "面试")
    resume_count = sum(term in all_text for term in resume_terms)
    if resume_count:
        add("resume_helper", min(3, resume_count), "文本包含简历结构字段")

    if any(term in all_text for term in ("会议记录", "会议纪要", "meeting", "minutes")):
        add("meeting_minutes", 4, "任务或附件指向会议记录")
    meeting_terms = ("参会", "议题", "决议", "发言", "待办", "会议时间")
    meeting_count = sum(term in all_text for term in meeting_terms)
    if meeting_count:
        add("meeting_minutes", min(4, meeting_count), "文本包含会议纪要字段")

    keyword_signals: dict[str, tuple[str, ...]] = {
        "grading": ("批改", "参考答案", "作答", "评分", "评语"),
        "classroom_interaction": (
            "课堂互动",
            "活动包",
            "活动序列",
            "举手",
            "选项人数",
            "课堂现象",
            "课堂观察",
            "课后总结",
            "课堂总结",
            "追问",
        ),
        "course_iteration": ("课程迭代", "旧课件", "更新课件", "教学大纲"),
        "lesson_design": ("教案", "教学设计", "互动题", "评分量规", "课堂练习", "练习题"),
        "teaching_report": ("教学报告", "汇总报告", "教学总结"),
        "notice_writer": ("通知", "通告", "润色通知"),
        "summary": ("摘要", "总结材料", "提取要点"),
        "todo_breakdown": ("待办", "行动项", "任务拆解"),
        "text_cleanup": ("规整", "清洗格式", "整理表格"),
        "format_check": ("公文格式", "格式检查", "格式规范"),
        "course_qa": ("课程资料", "教材", "讲义", "课件问答"),
        "personal_tutor": ("错题", "薄弱点", "答疑", "不会做"),
        "practice_helper": ("练习", "习题", "练习题"),
        "speaking_practice": ("口语", "发音", "英语对话"),
        "study_planner": ("学习计划", "规划学习", "学习目标"),
    }
    for agent, terms in keyword_signals.items():
        count = sum(term in all_text for term in terms)
        if count:
            add(agent, min(4, count * 2), f"任务包含{terms[0]}等关键词")

    # A short follow-up inherits the last selected agent only when that agent
    # belongs to the current role.  This is conversational state, not a new
    # cross-role capability.
    previous_agent = context.conversation_agent_id or _last_agent(context.recent_messages)
    if previous_agent in available and _is_short_follow_up(content) and not neutral_message:
        add(previous_agent, 3, "延续当前对话中的智能体")

    if not scores:
        return None
    agent, (score, reasons) = max(scores.items(), key=lambda item: item[1][0])
    return _RuleMatch(agent=agent, score=score, reason="；".join(dict.fromkeys(reasons)))


def _classifier_messages(
    context: RouteContext, available: tuple[AgentDefinition, ...]
) -> list[dict[str, str]]:
    allowed = [
        {"id": agent.id, "name": agent.name, "description": agent.description}
        for agent in available
    ]
    attachments = [
        {
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "headers": list(attachment.headers),
            "text_excerpt": attachment.text_excerpt[:1200],
            "status": attachment.status,
        }
        for attachment in context.attachments
    ]
    payload = {
        "role": context.role,
        "content": context.content,
        "attachments": attachments,
        "recent_messages": list(context.recent_messages[-6:]),
        "allowed_agents": allowed,
    }
    return [
        {
            "role": "system",
            "content": (
                "你是角色内智能体分类器。只能从 allowed_agents 中选择 agent，不能跨角色。"
                "只输出 JSON：agent、confidence（0 到 1）、reason、missing_inputs。"
                f" allowed_agents={json.dumps([agent['id'] for agent in allowed], ensure_ascii=False)}"
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _candidate_ids(
    available: tuple[AgentDefinition, ...], rule_match: _RuleMatch | None
) -> tuple[str, ...]:
    if rule_match is not None:
        return (rule_match.agent,)
    return tuple(agent.id for agent in available)


def _rule_confidence(score: int) -> float:
    if score >= 6:
        return 0.97
    if score >= 4:
        return 0.91
    if score >= 3:
        return 0.84
    if score >= 2:
        return 0.68
    return 0.55


def _is_tabular(attachment: RouteAttachment) -> bool:
    filename = attachment.filename.lower()
    return filename.endswith((".csv", ".xlsx", ".xls")) or attachment.content_type.lower() in {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


def _last_agent(messages: tuple[dict[str, Any], ...]) -> str | None:
    for message in reversed(messages):
        agent_id = message.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return agent_id
    return None


def _is_short_follow_up(content: str) -> bool:
    return len(content.strip()) <= 18 or any(
        phrase in content for phrase in ("继续", "再改", "再说说", "这个呢", "详细一点")
    )


def _is_neutral_message(content: str) -> bool:
    normalized = content.strip().lower().strip(" ，。！？!?.,~～")
    return normalized in {"你好", "您好", "嗨", "哈喽", "hello", "hi", "hey", "早上好", "下午好", "晚上好"}


def _missing_inputs_for_agent(agent_id: str, context: RouteContext) -> list[str]:
    attachments = context.attachments
    text = f"{context.content} {' '.join(attachment.filename for attachment in attachments)}".lower()
    if agent_id == "learning_analysis":
        if any(_is_tabular(attachment) for attachment in attachments):
            return []
        return ["匿名成绩、作业或练习统计表格"]
    if agent_id == "course_qa" and not attachments:
        return ["明确选择的课程资料"]
    if agent_id == "personal_tutor" and not attachments:
        return ["明确选择的错题、作业或薄弱点材料"]
    if agent_id == "resume_helper" and not any(
        term in text for term in ("简历", "resume", "cv", "项目经历", "教育背景")
    ):
        return ["简历文本或简历附件"]
    if agent_id == "meeting_minutes" and not any(
        term in text for term in ("会议", "meeting", "minutes", "议题", "参会")
    ):
        return ["会议记录文本或会议记录附件"]
    return []
