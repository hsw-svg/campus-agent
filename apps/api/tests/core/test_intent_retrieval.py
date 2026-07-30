import math
from collections.abc import Sequence

import pytest

from app.agents.intent_retrieval import (
    IntentQuery,
    IntentRetrievalError,
    SemanticIntentRetriever,
)
from app.agents.registry import AgentDefinition, RoutingProfile


def _agent(agent_id: str, intent: str, *examples: str) -> AgentDefinition:
    return AgentDefinition(
        id=agent_id,
        name=agent_id,
        description=intent,
        routing=RoutingProfile(intent=intent, examples=tuple(examples)),
    )


class KeywordEmbeddingProvider:
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for text in texts:
            if "简历" in text or "求职" in text:
                vectors.append([1.0, 0.0, 0.0])
            elif "计划" in text or "复习" in text:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


@pytest.mark.asyncio
async def test_semantic_retriever_orders_candidates_and_limits_top_k() -> None:
    provider = KeywordEmbeddingProvider()
    retriever = SemanticIntentRetriever(provider, candidate_count=2)
    agents = (
        _agent("resume", "优化求职简历", "改写简历项目经历"),
        _agent("planner", "制定学习计划", "制定期末复习计划"),
        _agent("other", "处理其他任务", "普通帮助"),
    )

    candidates = await retriever.retrieve(
        IntentQuery(role="student", content="帮我优化求职简历"),
        agents,
    )

    assert [candidate.agent_id for candidate in candidates] == ["resume", "planner"]
    assert candidates[0].similarity == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_semantic_retriever_reuses_profile_embeddings() -> None:
    provider = KeywordEmbeddingProvider()
    retriever = SemanticIntentRetriever(provider)
    agents = (
        _agent("resume", "优化求职简历", "改写简历"),
        _agent("planner", "制定学习计划", "安排复习"),
    )

    await retriever.retrieve(IntentQuery(role="student", content="优化简历"), agents)
    await retriever.retrieve(IntentQuery(role="student", content="制定计划"), agents)

    assert len(provider.calls) == 2
    assert len(provider.calls[0]) == 3
    assert len(provider.calls[1]) == 1
    assert "制定计划" in provider.calls[1][0]


@pytest.mark.asyncio
async def test_short_follow_up_adds_recent_context_to_query() -> None:
    provider = KeywordEmbeddingProvider()
    retriever = SemanticIntentRetriever(provider)
    agents = (_agent("resume", "优化求职简历", "改写简历"),)

    await retriever.retrieve(
        IntentQuery(
            role="student",
            content="继续",
            recent_messages=({"role": "user", "content": "帮我优化简历"},),
            conversation_agent_id="resume",
        ),
        agents,
    )

    assert "最近对话：帮我优化简历" in provider.calls[0][0]
    assert "当前会话智能体：resume" in provider.calls[0][0]


@pytest.mark.asyncio
async def test_role_indexes_do_not_leak_candidates_between_roles() -> None:
    provider = KeywordEmbeddingProvider()
    retriever = SemanticIntentRetriever(provider)

    student_candidates = await retriever.retrieve(
        IntentQuery(role="student", content="优化简历"),
        (_agent("resume", "优化求职简历", "改写简历"),),
    )
    admin_candidates = await retriever.retrieve(
        IntentQuery(role="admin", content="整理材料"),
        (_agent("summary", "总结行政材料", "提取材料要点"),),
    )

    assert [candidate.agent_id for candidate in student_candidates] == ["resume"]
    assert [candidate.agent_id for candidate in admin_candidates] == ["summary"]


class BrokenEmbeddingProvider:
    is_configured = True

    def __init__(self, vectors=None, error: Exception | None = None) -> None:
        self.vectors = vectors
        self.error = error

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.error is not None:
            raise self.error
        return self.vectors


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider",
    (
        BrokenEmbeddingProvider(error=RuntimeError("upstream unavailable")),
        BrokenEmbeddingProvider(vectors=[]),
        BrokenEmbeddingProvider(vectors=[[1.0], [1.0, 2.0]]),
        BrokenEmbeddingProvider(vectors=[[1.0], [math.nan]]),
        BrokenEmbeddingProvider(vectors=[[0.0], [1.0]]),
    ),
)
async def test_invalid_or_failed_embeddings_are_reported_as_retrieval_errors(
    provider,
) -> None:
    retriever = SemanticIntentRetriever(provider)
    agents = (_agent("resume", "优化求职简历", "改写简历"),)

    with pytest.raises(IntentRetrievalError):
        await retriever.retrieve(IntentQuery(role="student", content="优化简历"), agents)


@pytest.mark.asyncio
async def test_unconfigured_embedding_provider_is_unavailable() -> None:
    provider = BrokenEmbeddingProvider(vectors=[])
    provider.is_configured = False
    retriever = SemanticIntentRetriever(provider)

    with pytest.raises(IntentRetrievalError):
        await retriever.retrieve(
            IntentQuery(role="student", content="优化简历"),
            (_agent("resume", "优化求职简历", "改写简历"),),
        )
