import asyncio
import json

import pytest

from app.agents.intent_retrieval import IntentCandidate
from app.agents.router import AgentRouter, RouteAttachment, RouteContext
from app.core.errors import AppError


class FakeRouteClassifier:
    is_configured = True

    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    async def classify_route(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeCandidateRetriever:
    def __init__(self, *agent_ids: str) -> None:
        self.agent_ids = agent_ids
        self.calls = []

    async def retrieve(self, query, agents):
        self.calls.append((query, agents))
        return tuple(
            IntentCandidate(agent_id=agent_id, similarity=0.95 - index * 0.1)
            for index, agent_id in enumerate(self.agent_ids)
        )


class FailingCandidateRetriever:
    async def retrieve(self, query, agents):
        raise RuntimeError("embedding unavailable")


def test_manual_selection_skips_semantic_retrieval_and_intent_llm() -> None:
    classifier = FakeRouteClassifier(RuntimeError("must not be called"))
    retriever = FakeCandidateRetriever("study_planner")
    router = AgentRouter(classifier, retriever)

    decision = asyncio.run(
        router.route(
            RouteContext(role="student", content="帮我处理"),
            manual_agent_id="resume_helper",
        )
    )

    assert decision.agent == "resume_helper"
    assert decision.selection_source == "manual"
    assert classifier.calls == []
    assert retriever.calls == []


def test_semantic_candidates_are_decided_by_intent_llm() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"course_iteration","confidence":0.96,"reason":"用户明确要求生成 PPT"}'
    )
    retriever = FakeCandidateRetriever("course_iteration", "lesson_design", "learning_analysis")
    router = AgentRouter(classifier, retriever)

    decision = asyncio.run(
        router.route(RouteContext(role="teacher", content="生成极限运算法则的 PPT"))
    )

    assert retriever.calls
    assert classifier.calls
    assert decision.agent == "course_iteration"
    assert decision.selection_source == "semantic_llm"
    assert decision.candidates == (
        "course_iteration",
        "lesson_design",
        "learning_analysis",
    )


def test_classifier_receives_attachment_facts_but_not_raw_excerpt() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"learning_analysis","confidence":0.93,"reason":"匿名成绩表需要班级分析"}'
    )
    router = AgentRouter(classifier, FakeCandidateRetriever("learning_analysis", "lesson_design"))

    decision = asyncio.run(
        router.route(
            RouteContext(
                role="teacher",
                content="分析这份成绩表",
                attachments=(
                    RouteAttachment(
                        filename="scores.csv",
                        content_type="text/csv",
                        headers=("匿名编号", "得分"),
                        text_excerpt="STUDENT_SECRET_001,52",
                    ),
                ),
            )
        )
    )

    payload = json.loads(classifier.calls[0][1]["content"])
    assert payload["attachments"][0]["headers"] == ["匿名编号", "得分"]
    assert "STUDENT_SECRET_001" not in classifier.calls[0][1]["content"]
    assert decision.agent == "learning_analysis"
    assert decision.missing_inputs == ()


def test_candidate_outside_semantic_recall_falls_back_to_generic_chat() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"learning_analysis","confidence":0.99,"reason":"候选外结果"}'
    )
    router = AgentRouter(
        classifier,
        FakeCandidateRetriever("course_iteration", "lesson_design"),
    )

    decision = asyncio.run(
        router.route(RouteContext(role="teacher", content="生成课程材料"))
    )

    assert decision.agent is None
    assert decision.selection_source == "fallback"
    assert decision.requires_confirmation is False
    assert decision.candidates == ("course_iteration", "lesson_design")


@pytest.mark.parametrize(
    "response",
    (
        '{"agent":"resume_helper","confidence":0.42,"reason":"证据不足"}',
        '{"agent":null,"confidence":0.91,"reason":"普通聊天"}',
        "not-json",
        RuntimeError("classifier unavailable"),
    ),
)
def test_uncertain_or_failed_intent_llm_falls_back_without_confirmation(response) -> None:
    router = AgentRouter(
        FakeRouteClassifier(response),
        FakeCandidateRetriever("resume_helper", "study_planner"),
    )

    decision = asyncio.run(
        router.route(RouteContext(role="student", content="帮我处理一下"))
    )

    assert decision.agent is None
    assert decision.selection_source == "fallback"
    assert decision.requires_confirmation is False


def test_embedding_failure_lets_llm_classify_all_agents_for_role() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"resume_helper","confidence":0.91,"reason":"请求是简历优化"}'
    )
    router = AgentRouter(classifier, FailingCandidateRetriever())

    decision = asyncio.run(
        router.route(RouteContext(role="student", content="帮我优化简历"))
    )

    payload = json.loads(classifier.calls[0][1]["content"])
    allowed_ids = [agent["id"] for agent in payload["allowed_agents"]]
    assert len(allowed_ids) == 6
    assert "resume_helper" in allowed_ids
    assert decision.agent == "resume_helper"
    assert decision.selection_source == "llm_fallback"


def test_selected_agent_still_uses_deterministic_missing_input_check() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"learning_analysis","confidence":0.94,"reason":"需要分析学情"}'
    )
    router = AgentRouter(classifier, FakeCandidateRetriever("learning_analysis"))

    decision = asyncio.run(
        router.route(RouteContext(role="teacher", content="总结班级薄弱点"))
    )

    assert decision.agent == "learning_analysis"
    assert decision.missing_inputs == ("匿名成绩、作业或练习统计表格",)


def test_short_follow_up_context_is_forwarded_to_semantic_retrieval() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"resume_helper","confidence":0.93,"reason":"延续上一轮简历修改"}'
    )
    retriever = FakeCandidateRetriever("resume_helper", "study_planner")
    router = AgentRouter(classifier, retriever)

    decision = asyncio.run(
        router.route(
            RouteContext(
                role="student",
                content="继续优化",
                recent_messages=(
                    {"role": "user", "content": "帮我修改这份简历"},
                ),
                conversation_agent_id="resume_helper",
            )
        )
    )

    query, _ = retriever.calls[0]
    assert query.recent_messages[0]["content"] == "帮我修改这份简历"
    assert query.conversation_agent_id == "resume_helper"
    assert decision.agent == "resume_helper"


def test_manual_agent_cannot_cross_role_boundary() -> None:
    router = AgentRouter()

    with pytest.raises(AppError) as error:
        asyncio.run(
            router.route(
                RouteContext(role="student", content="处理一下"),
                manual_agent_id="learning_analysis",
            )
        )

    assert error.value.code == "agent_not_available"
