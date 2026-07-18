import asyncio

import pytest

from app.agents.router import AgentRouter, RouteAttachment, RouteContext
from app.core.errors import AppError


class FakeRouteClassifier:
    is_configured = True

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    async def classify_route(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.response


def test_grade_sheet_is_routed_to_teacher_learning_analysis_by_rules() -> None:
    router = AgentRouter()

    decision = asyncio.run(router.route(
        RouteContext(
            role="teacher",
            content="请分析这份成绩表，找出薄弱章节。",
            attachments=(
                RouteAttachment(
                    filename="匿名成绩表.csv",
                    content_type="text/csv",
                    headers=("匿名编号", "章节", "得分", "满分"),
                    text_excerpt="匿名编号 | 章节 | 得分 | 满分\nA01 | 函数 | 72 | 100",
                ),
            ),
        )
    ))

    assert decision.agent == "learning_analysis"
    assert decision.confidence >= 0.8
    assert decision.selection_source == "rule"
    assert decision.requires_confirmation is False


def test_greeting_does_not_inherit_learning_analysis_agent_from_previous_turn() -> None:
    router = AgentRouter()

    decision = asyncio.run(router.route(
        RouteContext(
            role="teacher",
            content="你好",
            conversation_agent_id="learning_analysis",
            recent_messages=({"role": "assistant", "agent_id": "learning_analysis", "content": "分析完成"},),
            attachments=(
                RouteAttachment(
                    filename="高等数学学情表.csv",
                    content_type="text/csv",
                    headers=("匿名编号", "极限得分"),
                    text_excerpt="匿名编号 | 极限得分\nA01 | 90",
                ),
            ),
        )
    ))

    assert decision.agent is None


def test_uncertain_route_uses_structured_llm_output() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"resume_helper","confidence":0.91,"reason":"文本包含项目经历和求职目标","missing_inputs":[]}'
    )
    router = AgentRouter(classifier=classifier)

    decision = asyncio.run(router.route(
        RouteContext(role="student", content="帮我看看这段内容", recent_messages=())
    ))

    assert decision.agent == "resume_helper"
    assert decision.confidence == 0.91
    assert decision.selection_source == "llm"
    assert classifier.calls
    assert "resume_helper" in classifier.calls[0][0]["content"]


def test_llm_cannot_route_outside_the_current_role() -> None:
    classifier = FakeRouteClassifier(
        '{"agent":"learning_analysis","confidence":0.99,"reason":"bad","missing_inputs":[]}'
    )
    router = AgentRouter(classifier=classifier)

    with pytest.raises(AppError) as error:
        asyncio.run(router.route(RouteContext(role="student", content="帮我处理一下")))

    assert error.value.code == "agent_not_available"
