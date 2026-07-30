import asyncio
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol

from app.agents.registry import AgentDefinition
from app.integrations.embedding.providers import EmbeddingProvider


DEFAULT_INTENT_CANDIDATE_COUNT = 3


class IntentRetrievalError(RuntimeError):
    """Semantic intent candidates could not be produced safely."""


@dataclass(frozen=True)
class IntentQuery:
    role: str
    content: str
    recent_messages: tuple[dict[str, Any], ...] = ()
    conversation_agent_id: str | None = None


@dataclass(frozen=True)
class IntentCandidate:
    agent_id: str
    similarity: float


class IntentCandidateRetriever(Protocol):
    async def retrieve(
        self,
        query: IntentQuery,
        agents: tuple[AgentDefinition, ...],
    ) -> tuple[IntentCandidate, ...]: ...


@dataclass(frozen=True)
class _Prototype:
    agent_id: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class _RoleIndex:
    fingerprint: str
    dimensions: int
    prototypes: tuple[_Prototype, ...]


class SemanticIntentRetriever:
    def __init__(
        self,
        provider: EmbeddingProvider,
        candidate_count: int = DEFAULT_INTENT_CANDIDATE_COUNT,
    ) -> None:
        if candidate_count < 1:
            raise ValueError("candidate_count must be positive")
        self.provider = provider
        self.candidate_count = candidate_count
        self._indexes: dict[str, _RoleIndex] = {}
        self._index_lock = Lock()

    async def retrieve(
        self,
        query: IntentQuery,
        agents: tuple[AgentDefinition, ...],
    ) -> tuple[IntentCandidate, ...]:
        if not agents:
            return ()
        if not getattr(self.provider, "is_configured", False):
            raise IntentRetrievalError("embedding provider is not configured")
        try:
            return await asyncio.to_thread(self._retrieve_sync, query, agents)
        except IntentRetrievalError:
            raise
        except Exception as error:
            raise IntentRetrievalError("embedding provider failed") from error

    def _retrieve_sync(
        self,
        query: IntentQuery,
        agents: tuple[AgentDefinition, ...],
    ) -> tuple[IntentCandidate, ...]:
        fingerprint = _routing_fingerprint(agents)
        query_text = _semantic_query_text(query)
        index = self._indexes.get(query.role)

        if index is None or index.fingerprint != fingerprint:
            with self._index_lock:
                index = self._indexes.get(query.role)
                if index is None or index.fingerprint != fingerprint:
                    index, query_vector = self._build_index(
                        query.role,
                        fingerprint,
                        query_text,
                        agents,
                    )
                    self._indexes[query.role] = index
                else:
                    query_vector = self._embed_query(query_text, index.dimensions)
        else:
            query_vector = self._embed_query(query_text, index.dimensions)

        agent_order = {agent.id: position for position, agent in enumerate(agents)}
        scores: dict[str, float] = {}
        for prototype in index.prototypes:
            similarity = _cosine_similarity(query_vector, prototype.vector)
            scores[prototype.agent_id] = max(
                similarity,
                scores.get(prototype.agent_id, -1.0),
            )

        ordered = sorted(
            scores.items(),
            key=lambda item: (-item[1], agent_order[item[0]]),
        )
        return tuple(
            IntentCandidate(agent_id=agent_id, similarity=similarity)
            for agent_id, similarity in ordered[: self.candidate_count]
        )

    def _build_index(
        self,
        role: str,
        fingerprint: str,
        query_text: str,
        agents: tuple[AgentDefinition, ...],
    ) -> tuple[_RoleIndex, tuple[float, ...]]:
        prototype_owners: list[str] = []
        prototype_texts: list[str] = []
        for agent in agents:
            for example in agent.routing.examples:
                prototype_owners.append(agent.id)
                prototype_texts.append(
                    f"意图：{agent.routing.intent}\n代表表达：{example}"
                )

        vectors = self.provider.embed([query_text, *prototype_texts])
        normalized = _normalize_vectors(vectors, 1 + len(prototype_texts))
        query_vector = normalized[0]
        prototypes = tuple(
            _Prototype(agent_id=agent_id, vector=vector)
            for agent_id, vector in zip(prototype_owners, normalized[1:], strict=True)
        )
        return (
            _RoleIndex(
                fingerprint=fingerprint,
                dimensions=len(query_vector),
                prototypes=prototypes,
            ),
            query_vector,
        )

    def _embed_query(self, query_text: str, dimensions: int) -> tuple[float, ...]:
        vectors = _normalize_vectors(self.provider.embed([query_text]), 1)
        if len(vectors[0]) != dimensions:
            raise IntentRetrievalError("embedding dimensions changed")
        return vectors[0]


def _routing_fingerprint(agents: tuple[AgentDefinition, ...]) -> str:
    payload = [
        {
            "id": agent.id,
            "intent": agent.routing.intent,
            "examples": agent.routing.examples,
            "exclusions": agent.routing.exclusions,
        }
        for agent in agents
    ]
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _semantic_query_text(query: IntentQuery) -> str:
    content = query.content.strip()
    if not _is_short_follow_up(content):
        return content

    recent = [
        str(message.get("content", "")).strip()
        for message in query.recent_messages[-3:]
        if str(message.get("content", "")).strip()
    ]
    parts = [f"当前请求：{content}"]
    if query.conversation_agent_id:
        parts.append(f"当前会话智能体：{query.conversation_agent_id}")
    if recent:
        parts.append(f"最近对话：{' | '.join(recent)}")
    return "\n".join(parts)


def _is_short_follow_up(content: str) -> bool:
    return len(content) <= 18 or any(
        phrase in content for phrase in ("继续", "再改", "再说说", "这个呢", "详细一点")
    )


def _normalize_vectors(
    vectors: Sequence[Sequence[float]],
    expected_count: int,
) -> tuple[tuple[float, ...], ...]:
    if len(vectors) != expected_count:
        raise IntentRetrievalError("embedding count mismatch")

    normalized = tuple(tuple(float(value) for value in vector) for vector in vectors)
    if not normalized or not normalized[0]:
        raise IntentRetrievalError("embedding vector is empty")
    dimensions = len(normalized[0])
    for vector in normalized:
        if len(vector) != dimensions:
            raise IntentRetrievalError("embedding dimensions are inconsistent")
        if not all(math.isfinite(value) for value in vector):
            raise IntentRetrievalError("embedding contains non-finite values")
        if math.isclose(sum(value * value for value in vector), 0.0):
            raise IntentRetrievalError("embedding vector has zero magnitude")
    return normalized


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise IntentRetrievalError("embedding dimensions are inconsistent")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if math.isclose(left_norm, 0.0) or math.isclose(right_norm, 0.0):
        raise IntentRetrievalError("embedding vector has zero magnitude")
    return dot / (left_norm * right_norm)
