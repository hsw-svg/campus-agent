# Agent Intent Routing

## 1. Scope / Trigger

This contract applies whenever an agent is added, renamed, removed, or made available for automatic routing. It also applies when changing `AgentRouter`, the embedding provider, the route-classification prompt, or any route/stream/retry dependency wiring.

The project uses a strict two-layer automatic route: semantic embeddings retrieve candidates, then the existing Chat provider makes the final structured intent decision. Keyword scores must not directly invoke a specialist.

## 2. Signatures

The registry owns route metadata:

```python
@dataclass(frozen=True)
class RoutingProfile:
    intent: str
    examples: tuple[str, ...]
    exclusions: tuple[str, ...] = ()

@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    description: str
    routing: RoutingProfile
```

Candidate retrieval is isolated from routing and from the concrete embedding SDK:

```python
class IntentCandidateRetriever(Protocol):
    async def retrieve(
        self,
        query: IntentQuery,
        agents: tuple[AgentDefinition, ...],
    ) -> tuple[IntentCandidate, ...]: ...
```

The public service boundary remains:

```python
await AgentRouter(classifier, candidate_retriever).route(
    context,
    manual_agent_id=None,
) -> RouteDecision
```

## 3. Contracts

- `manual_agent_id`: highest priority; validate against the current role, then skip Embedding and Intent LLM.
- Automatic route candidates: ordered Top 3 from the current role only.
- Semantic profile cache: process-local, keyed by role and a fingerprint of ids, intents, examples, and exclusions. It must be lazy; application startup must not call an external model.
- Intent LLM: always use the existing Chat provider and `CHAT_BASE_URL`, `CHAT_API_KEY`, `CHAT_MODEL`. Do not add separate intent-model settings.
- Embeddings: use `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`. The synchronous provider call must run outside the event loop.
- Classifier input: current content, limited recent messages, conversation agent id, candidate profiles, and structured attachment facts. Do not include attachment `text_excerpt` or raw file rows.
- Classifier output: JSON `agent: str | null`, `confidence: float [0,1]`, `reason: non-empty str`.
- A non-null agent must belong to the supplied candidate set. One message selects at most one specialist.
- `RouteDecision` keeps its existing field shape. Stable `selection_source` values are `manual`, `semantic_llm`, `llm_fallback`, and `fallback`.
- `requires_confirmation` must remain `False` for automatic low-confidence or provider-failure paths because the current frontend has no candidate confirmation action.
- REST and SSE route fields remain compatible. Candidate ids and selection source continue to be stored in existing AgentRun fields; no database migration is required.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Role has no agents | Raise `AppError(code="role_not_supported")`. |
| Manual id is outside role | Raise `AppError(code="agent_not_available")`. |
| Chat provider is not configured | Return ordinary-chat `fallback`; do not run Embedding. |
| Embedding is unconfigured, fails, or returns invalid vectors | Run Intent LLM with all agents for the current role and use `llm_fallback` on success. |
| Retriever returns empty or foreign candidates | Treat retrieval as unavailable; use the role-scoped full list. |
| Intent LLM returns invalid JSON, throws, or returns a candidate-outside id | Return ordinary-chat `fallback`; never invoke a specialist. |
| Intent LLM returns null or confidence below `0.8` | Return ordinary-chat `fallback` with `requires_confirmation=False`. |
| Valid candidate has confidence at least `0.8` | Return the selected agent and compute missing inputs deterministically from route context. |

Do not expose provider exception details, prompts, vectors, raw attachment content, or credentials in `reason`, API responses, or logs.

## 5. Good / Base / Bad Cases

- Good: "Generate a PPT about limits" retrieves course iteration, lesson design, and learning analysis; Intent LLM chooses `course_iteration`; source is `semantic_llm`.
- Base: Embedding is temporarily unavailable; Intent LLM sees all six agents for the teacher role and safely chooses one; source is `llm_fallback`.
- Base: "Hello" yields `agent=null` and continues through ordinary chat without a confirmation error.
- Bad: embedding similarity directly invokes `course_iteration` without an Intent LLM call.
- Bad: an attached grade sheet is serialized with row-level contents into the intent-classification prompt.
- Bad: an LLM response names an agent outside the recalled candidates and the router executes it.

## 6. Tests Required

- Registry test: every role has unique agent ids and every agent has a non-empty intent plus at least two non-empty examples.
- Retrieval unit tests: stable ordering, Top-K, role isolation, short-follow-up context, profile-cache reuse, and invalid count/dimension/NaN/zero vectors.
- Router unit tests: manual bypass, semantic candidate selection, candidate-outside rejection, deterministic missing inputs, low confidence, null output, invalid JSON, classifier exception, and embedding-to-full-list fallback.
- Attachment assertion: structured headers may reach Intent LLM; a unique raw row marker must not.
- API regression: `/route`, message SSE, and AgentRun retry use the same Router dependency; candidate ids and `selection_source` survive the API boundary.
- All tests must use fake providers. Do not make billable Chat or Embedding requests during validation.

## 7. Wrong vs Correct

### Wrong

```python
if "ppt" in content:
    return RouteDecision(agent="course_iteration", confidence=0.97)
```

This bypasses semantic recall and the mandatory final Intent LLM decision, and each new agent expands a centralized conflict-prone rule table.

### Correct

```python
candidates = await candidate_retriever.retrieve(query, list_agents(role))
result = parse_json(
    await classifier.classify_route(candidate_prompt(context, candidates)),
    LLMRouteOutput,
)
if result.agent not in {candidate.agent_id for candidate in candidates}:
    return ordinary_chat_fallback(candidates)
```

Add or refine an agent by editing its `RoutingProfile`; only add specialized execution and input policy code when the agent itself needs new business behavior.
