# Technical Design: Agent Streaming Progress

## Scope and boundaries

The public boundary remains the existing same-origin `POST /api/conversations/{id}/messages/stream` SSE endpoint. The change adds a typed internal executor stream and enriches the existing `tool_status` event; it does not add a second transport, persistence model, or database table.

The first-class streaming paths are:

- plain model replies through `GenericChatExecutor`;
- course iteration, including the structured slide-deck branch;
- deterministic learning analysis;
- a heartbeat fallback for executors that still expose only `execute`, so classroom, lesson-design, student, admin, and resume flows show progress without being forced into a large refactor.

The teacher workspace owns the small progress panel. The resume assistant continues consuming the same SSE stream and ignores the new optional status fields it does not render.

## Internal execution stream

Add an internal `AgentExecutionEvent` contract next to `AgentResult`:

```text
status  -> safe AgentProgress(step_id, phase, state, label, detail?, count?)
delta   -> visible assistant text fragment
result  -> final AgentResult
```

`AgentProgress.phase` is a closed vocabulary such as `routing`, `context`, `retrieval`, `model`, `validation`, `artifact`, and `complete`. `state` is `active`, `completed`, or `failed`. `detail` is a short, sanitized UI summary; it must never contain prompts, raw attachment rows, model hidden reasoning, provider exceptions, or credentials.

`AgentExecutor` keeps its existing `execute` contract. Executors that can provide meaningful incremental output expose an additional `stream(request)` method. `stream_assistant_reply` detects that method and otherwise wraps `execute(request)` in a cancellable heartbeat adapter. This preserves existing executors while making the migration incremental.

### Executor behavior

1. `GenericChatExecutor.stream` forwards each `ChatProvider.stream_reply` fragment as an internal `delta`, then emits the final result. Its `execute` implementation can collect the same stream, preserving current callers.
2. `CourseIterationExecutor.stream` emits retrieval and model-generation phases. The non-slide fallback can forward visible text through the generic stream. The structured slide-deck model output remains an internal buffer because raw JSON is not a user-facing answer; it emits throttled safe progress such as “正在生成课件结构（已接收模型输出）”, then emits the validated Markdown/Artifact only after normalization succeeds. Repair attempts are represented as a validation/retry step.
3. `LearningAnalysisExecutor.stream` emits table-reading, statistics, validation, and artifact phases around the deterministic skill calls. It does not include file rows, student identifiers, or generated hidden analysis in status details.
4. Other executors use the service heartbeat fallback until they gain a specialized stream implementation. The final result and current error semantics remain unchanged.

## Public SSE contract

Keep the existing event names, including `route_decision`, and add these optional fields to `tool_status`:

```json
{
  "status": "model_generation",
  "step_id": "course-iteration-model",
  "phase": "model",
  "state": "active",
  "label": "正在生成课程迭代内容",
  "detail": "已接收模型输出片段",
  "count": 12,
  "agent_id": "course_iteration",
  "run_id": "...",
  "sequence": 4
}
```

The legacy `status` field remains populated for existing consumers. `streaming.py` updates its event vocabulary to include the already-used `route_decision`. The service serializes internal status events into `tool_status`, forwards visible deltas immediately, and sends one final delta only when no visible fragments were streamed or when the normalized result has not already been displayed. Artifact creation, message persistence, `done`, `error`, and cancellation handling stay in the current service boundary.

## Frontend state and presentation

`api.ts` expands the typed `StreamEvent` payload helpers without requiring a new event name. `useWorkspaceChat` owns a normalized `progressSteps` list and updates it by `step_id`; legacy status-only events are mapped to a single compatible step. The hook resets progress on new/cleared/opened conversations, marks active steps complete on `done`, and exposes the list alongside the existing `toolStatus`/`runStatus` values.

Add `AgentProgressPanel.tsx` as a single reusable component:

- compact max-width card, not a full-width message bubble or log stream;
- expanded while `isAiTyping`, showing the current step and a short list of completed/active steps;
- collapses to one summary row after completion, failure, or stop, with a button to reopen;
- has `aria-live="polite"`, a clear “停止生成” action while running, and no independent vertical scroll owner;
- uses opacity/short transitions and respects the existing reduced-motion behavior.

Render it in the course conversation after the assistant message list and before the conversation-end anchor, and in the standalone teacher-agent execution state. The actual assistant message continues to render normal text deltas; structured reports/PPT previews remain the final normalized output. No raw process event list is inserted into message content.

## Compatibility, failure, and cancellation

- Unknown optional `tool_status` fields are safe for existing clients; `route_decision` is made explicit in the backend type vocabulary.
- If a model/provider fails, mark the active progress step failed, emit the existing `error`, and do not create a partial assistant message or Artifact.
- If the browser aborts the stream, cancel any executor task/iterator and retain the existing `stream_cancelled` AgentRun behavior.
- If a specialized stream raises during normalization, the service uses the same error mapping as the current `execute` path.
- Do not expose raw exception details in progress events; retain them only where the existing internal error handling already permits them.

## Verification strategy

- Backend unit/API tests assert ordering of status, incremental deltas, artifact, and done events; assert that course/learning progress never contains raw student identifiers or prompts.
- Frontend type check and build validate the new state/component integration. Docker-served UI verification checks the compact panel, live step updates, collapse behavior, and absence of raw process logs in message bubbles.
- Run `git diff --check` and the directly affected API test subsets before the full backend suite.
