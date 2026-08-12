"""Role-scoped semantic retrieval and Intent LLM routing decisions."""

import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.agents.intent_retrieval import (
    IntentCandidateRetriever,
    IntentQuery,
)
from app.agents.registry import AgentDefinition, is_agent_available_for_role, list_agents
from app.core.errors import AppError
from app.core.json_guard import parse_json
from app.courses.context import CourseLearningContext


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
    course: CourseLearningContext | None = None


@dataclass(frozen=True)
class RouteDecision:
    agent: str | None
    confidence: float
    reason: str
    missing_inputs: tuple[str, ...] = ()
    selection_source: str = "fallback"
    candidates: tuple[str, ...] = ()
    requires_confirmation: bool = False


class LLMRouteOutput(BaseModel):
    agent: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=1000)


class AgentRouter:
    """Retrieve role-scoped candidates, then let the Intent LLM choose one."""

    def __init__(
        self,
        classifier: RouteClassifier | None = None,
        candidate_retriever: IntentCandidateRetriever | None = None,
        confidence_threshold: float = ROUTE_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.classifier = classifier
        self.candidate_retriever = candidate_retriever
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
            return RouteDecision(
                agent=manual_agent_id,
                confidence=1.0,
                reason="用户手动选择了该智能体。",
                missing_inputs=tuple(_missing_inputs_for_agent(manual_agent_id, context)),
                selection_source="manual",
                candidates=(manual_agent_id,),
            )

        classifier = self.classifier
        if classifier is None or not self._can_classify():
            return self._chat_fallback_decision(
                tuple(agent.id for agent in available),
                "Intent LLM 未配置，已进入普通聊天。",
            )

        candidates, similarities, retrieval_succeeded = await self._retrieve_candidates(
            context,
            available,
        )
        candidate_ids = tuple(agent.id for agent in candidates)
        classification_source = "semantic_llm" if retrieval_succeeded else "llm_fallback"

        try:
            raw = await classifier.classify_route(
                _classifier_messages(context, candidates, similarities)
            )
            llm_result = parse_json(raw, LLMRouteOutput)
        except Exception:
            return self._chat_fallback_decision(
                candidate_ids,
                "Intent LLM 结果不可用，已进入普通聊天。",
            )

        if llm_result.agent is not None and llm_result.agent not in candidate_ids:
            return self._chat_fallback_decision(
                candidate_ids,
                "Intent LLM 返回了候选范围外的智能体，已进入普通聊天。",
                confidence=llm_result.confidence,
            )

        if llm_result.agent is None or llm_result.confidence < self.confidence_threshold:
            return self._chat_fallback_decision(
                candidate_ids,
                llm_result.reason,
                confidence=llm_result.confidence,
            )

        self._ensure_agent_available(context.role, llm_result.agent)
        return RouteDecision(
            agent=llm_result.agent,
            confidence=llm_result.confidence,
            reason=llm_result.reason,
            missing_inputs=tuple(_missing_inputs_for_agent(llm_result.agent, context)),
            selection_source=classification_source,
            candidates=candidate_ids,
        )

    async def _retrieve_candidates(
        self,
        context: RouteContext,
        available: tuple[AgentDefinition, ...],
    ) -> tuple[tuple[AgentDefinition, ...], dict[str, float], bool]:
        if self.candidate_retriever is None:
            return available, {}, False

        try:
            retrieved = await self.candidate_retriever.retrieve(
                IntentQuery(
                    role=context.role,
                    content=context.content,
                    recent_messages=context.recent_messages,
                    conversation_agent_id=context.conversation_agent_id,
                ),
                available,
            )
        except Exception:
            return available, {}, False

        definitions = {agent.id: agent for agent in available}
        ordered_ids: list[str] = []
        similarities: dict[str, float] = {}
        for candidate in retrieved:
            if candidate.agent_id not in definitions or candidate.agent_id in similarities:
                continue
            ordered_ids.append(candidate.agent_id)
            similarities[candidate.agent_id] = candidate.similarity
        if not ordered_ids:
            return available, {}, False
        return tuple(definitions[agent_id] for agent_id in ordered_ids), similarities, True

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
    def _chat_fallback_decision(
        candidates: tuple[str, ...],
        reason: str,
        *,
        confidence: float = 0.0,
    ) -> RouteDecision:
        return RouteDecision(
            agent=None,
            confidence=confidence,
            reason=reason,
            selection_source="fallback",
            candidates=candidates,
            requires_confirmation=False,
        )


def _classifier_messages(
    context: RouteContext,
    candidates: tuple[AgentDefinition, ...],
    similarities: dict[str, float],
) -> list[dict[str, str]]:
    allowed = [
        {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "intent": agent.routing.intent,
            "examples": list(agent.routing.examples),
            "exclusions": list(agent.routing.exclusions),
            "semantic_similarity": similarities.get(agent.id),
        }
        for agent in candidates
    ]
    attachments = [
        {
            "filename": attachment.filename,
            "content_type": attachment.content_type,
            "headers": list(attachment.headers),
            "status": attachment.status,
        }
        for attachment in context.attachments
    ]
    payload = {
        "role": context.role,
        "content": context.content,
        "attachments": attachments,
        "recent_messages": list(context.recent_messages[-6:]),
        "conversation_agent_id": context.conversation_agent_id,
        "course": (
            {
                "course_id": context.course.course_id,
                "course_name": context.course.course_name,
                "description": context.course.description,
                "category": context.course.category,
                "chapter_id": context.course.chapter_id,
                "chapter_title": context.course.chapter_title,
                "chapter_summary": context.course.chapter_summary,
                "knowledge_points": list(context.course.knowledge_points),
            }
            if context.course is not None
            else None
        ),
        "allowed_agents": allowed,
    }
    allowed_ids = [agent["id"] for agent in allowed]
    return [
        {
            "role": "system",
            "content": (
                "你是角色内智能体意图分类器。结合当前请求、有限对话上下文、附件结构事实和候选边界，"
                "最多选择一个最匹配的智能体。只能从 allowed_agents 中选择 agent，不能跨角色或候选范围。"
                "如果请求只是寒暄、通用聊天、证据不足或没有候选适合，agent 必须为 null。"
                "只输出 JSON：agent、confidence（0 到 1）、reason。"
                f" allowed_agents={json.dumps(allowed_ids, ensure_ascii=False)}"
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _is_tabular(attachment: RouteAttachment) -> bool:
    filename = attachment.filename.lower()
    return filename.endswith((".csv", ".xlsx", ".xls")) or attachment.content_type.lower() in {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }


def _missing_inputs_for_agent(agent_id: str, context: RouteContext) -> list[str]:
    attachments = context.attachments
    text = f"{context.content} {' '.join(attachment.filename for attachment in attachments)}".lower()
    if agent_id == "learning_analysis":
        if any(_is_tabular(attachment) for attachment in attachments):
            return []
        return ["匿名成绩、作业或练习统计表格"]
    if agent_id == "course_qa" and not attachments and context.course is None:
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
