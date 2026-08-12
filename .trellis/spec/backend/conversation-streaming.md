# Conversation Streaming and Agent Progress Contract

## 1. Scope / Trigger

This contract applies when a conversation agent needs to expose incremental text or safe execution progress through the existing same-origin SSE endpoint:

`POST /api/conversations/{conversation_id}/messages/stream`

It covers the backend executor boundary, SSE serialization, and the frontend progress projection consumed by `useWorkspaceChat`. It is required for new agent stages, new `tool_status` fields, or any executor that changes from final-result-only execution to streaming.

## 2. Signatures

Backend executors keep the compatibility method:

```python
async def execute(request: AgentRequest) -> AgentResult: ...
```

Incremental executors may additionally implement:

```python
def stream(request: AgentRequest) -> AsyncIterator[AgentExecutionEvent]: ...
```

`AgentExecutionEvent.type` is one of `status`, `delta`, or `result`. The service adapter `_stream_executor` uses `stream` when available and emits cancellable progress heartbeats for legacy `execute`-only executors.

Frontend consumers use the shared boundary decoder:

```typescript
progressStepFromEvent(event: StreamEvent): AgentProgressStep | null
```

Rendering components consume `AgentProgressStep[]`; they do not parse raw SSE fields independently.

## 3. Contracts

### Internal progress

`AgentProgress` contains:

- `step_id`: stable identifier for updates to the same step;
- `phase`: `routing | context | retrieval | model | validation | artifact | complete`;
- `state`: `active | completed | failed`;
- `label`: short, user-facing Chinese summary;
- optional `detail` and numeric `count`.

### Public SSE

Keep the existing event names: `message_start`, `route_decision`, `delta`, `tool_status`, `artifact`, `done`, and `error`. `tool_status` retains its legacy string `status` and may add:

```json
{
  "status": "model_active",
  "step_id": "course-iteration-model",
  "phase": "model",
  "state": "active",
  "label": "正在生成课程迭代内容",
  "detail": "已接收模型输出片段",
  "count": 8,
  "agent_id": "course_iteration",
  "run_id": "...",
  "sequence": 4
}
```

Visible plain-text model fragments are sent as `delta` immediately. Structured slide-deck JSON remains internal until validation and Markdown/Artifact normalization finish. The service sends a final delta only when no equivalent visible text has already been forwarded.

For `role == "student"`, every visible delta and the persisted assistant result pass through the shared student-brand contract. `StudentBrandStreamFilter` retains a possible trailing prefix across delta boundaries, so fragments such as `"Deep"` and `"Tutor助手发现"` become `"AI 学伴发现"` without briefly exposing a partial internal brand. `normalize_student_visible_text` applies the same replacements to the final `AgentResult.text` before persistence. Non-student streams, integration routes, logs, and engineering identifiers remain unchanged.

### Safety boundary

Progress fields must not contain hidden chain-of-thought, prompts, provider exceptions, credentials, raw attachment rows, or student identifiers. Learning-analysis progress is limited to anonymous stage summaries and aggregate counts.

### Conversation placement and scroll ownership

The teacher progress panel is part of the conversation flow and must render after the message list, immediately before the conversation-end anchor. The course conversation has one vertical scroll owner: the chat section. On initial history load or reopening the same conversation, scroll that container to the end anchor after messages and generated-report metadata have mounted. Do not use a course-level `scrollIntoView({ block: "start" })` effect to focus a restored report, because it overrides the latest-message position. Standalone report views may keep their own report focus behavior.

## 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Executor implements `stream` | Forward status and visible delta events, then require one result event. |
| Executor implements only `execute` | Run it in a cancellable task and emit safe model heartbeats until completion. |
| No result event is produced | Raise `agent_stream_did_not_complete`; emit the existing safe error response. |
| Model/provider or normalization failure | Mark the active progress step failed, then preserve the existing `error` mapping. |
| Browser aborts the request | Cancel and await the fallback task/iterator; do not leave a background execution running. |
| Unknown optional status fields | Existing SSE consumers ignore them and continue processing `done`/`error`. |
| Invalid learning table | Emit a failed validation stage and return the existing `learning_analysis_input_invalid` error without exposing rows. |
| Student internal brand is split across deltas | Buffer the possible brand prefix, emit only normalized visible text, and persist the identical normalized result. |
| Teacher/admin response contains an engineering integration name | Preserve it; student-brand normalization is role-scoped. |

## 5. Good / Base / Bad Cases

- **Good:** Generic chat forwards `“第”`, `“一”`, `“步”` as three deltas, then persists one combined assistant message.
- **Base:** A legacy classroom executor emits `model_active` heartbeats and one final result without requiring an executor rewrite.
- **Good:** Course iteration reports retrieval, generation, validation, and artifact stages while keeping raw JSON private.
- **Bad:** A `tool_status.detail` includes a prompt, a spreadsheet row, a student ID, or a provider exception.
- **Bad:** The frontend appends a normalized final response after already displaying the same text fragments, duplicating the assistant answer.
- **Bad:** A progress panel creates its own vertical scroll container inside the conversation scroll owner.
- **Bad:** Apply a regex independently to each delta; a provider can split a controlled brand between chunks and leak both halves.

## 6. Tests Required

- API conversation stream test: assert multiple visible `delta` events arrive before `done` and that model status includes active/completed stages.
- Course-iteration executor test: assert safe retrieval/model/validation/artifact status ordering and no raw JSON leakage.
- Learning-analysis API test: assert context/model/validation/artifact phases and absence of an anonymous row identifier from serialized status.
- Legacy-executor test: assert heartbeat fallback completes and cancellation awaits the background task.
- Frontend type/build check: assert `progressStepFromEvent` handles enriched and legacy `tool_status` payloads; run lint/typecheck and production build.
- Student branding tests: cover compact/spaced/case-insensitive variants, assistant/teaching-assistant suffixes, arbitrary delta splits, SSE-visible equality, and persisted-history equality.
- Docker-served browser check: assert the progress panel is compact, expandable while running, collapsed after completion, and old full-dialogue thinking animations are absent.

## 7. Wrong vs Correct

### Wrong

```python
yield stream_event("tool_status", {
    "status": "thinking",
    "detail": raw_prompt_or_model_reasoning,
})
```

This leaks internal model material and gives each frontend consumer an unstable payload to interpret.

### Correct

```python
yield progress_event(
    step_id="learning-analysis-statistics",
    phase="model",
    state="active",
    label="正在计算班级学习统计",
)
```

The service serializes this safe internal event into the existing `tool_status` SSE event, and the frontend maps it once through `progressStepFromEvent`.

### Wrong: per-delta replacement

```python
yield stream_event("delta", {"text": INTERNAL_BRAND_RE.sub("AI 学伴", raw_delta)})
```

This leaks `"Deep"` followed by `"Tutor助手"` when the controlled term crosses a chunk boundary.

### Correct: stateful student-visible filtering

```python
visible_delta = student_brand_filter.feed(raw_delta)
if visible_delta:
    yield stream_event("delta", {"text": visible_delta})
```

Flush the filter at result completion, normalize `AgentResult.text` through the same contract, then persist it.
