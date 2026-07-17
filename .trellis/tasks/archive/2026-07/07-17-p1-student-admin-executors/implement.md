# 学生与行政 Executor 执行计划

## Baseline and safeguards

- [x] Read parent PRD/design and backend spec indexes; record current `git status --short`.
- [x] Run focused baseline tests for agent architecture, routing, classroom, and stage 6/7 API paths.
- [x] Keep the existing uncommitted `AGENT.md`/`AGENTS.md`/`CLAUDE.md` changes outside this child’s implementation scope.

## Contract and context policy

- [x] Add Pydantic output models and deterministic Markdown serializers in the agents/skills layer.
- [x] Extend `ContextPolicy` with an explicit opt-out for implicit current-conversation attachments; preserve the default behavior for existing agents.
- [x] Configure the four P1 AgentSpecs with prompts, input contracts, context policies, executor ids and skill declarations.
- [x] Add role subpackages and export/import wiring without changing the public FastAPI request shape.

## Executors and integration

- [x] Implement the four independent Executors using the shared provider helper and strict JSON parsing.
- [x] Register each executor in `AgentExecutorRegistry` and ensure no P1 id falls through to `GenericChatExecutor`.
- [x] Return one stable Artifact per successful execution with source citations, structured `data`, Markdown `content`, and validation metadata.
- [x] Verify admin content-only behavior does not retrieve current uploads unless attachment ids are explicitly selected.

## Tests

- [x] Add unit tests for every output schema, prompt/parse path, empty/invalid output, missing selected material, and deterministic Markdown.
- [x] Add API tests for student/admin successful streams, Artifact listing/export, needs-input, failed/retry, and SSE event payloads.
- [x] Add workspace/role isolation tests for selected attachment/artifact ids and citation filtering.
- [x] Run `cd apps/api; uv run --extra dev python -m pytest -q` and record any environment-only failure.

全量验证：工作区内基目录运行 `uv run --extra dev python -m pytest -q --basetemp .pytest-tmp-p1`，结果为 `83 passed, 1 deselected`。不指定基目录时，pytest 因系统临时目录权限产生 7 个 fixture setup 错误；非业务断言失败。

## Handoff

- [x] Summarize stable agent ids, Artifact types, output fields, SSE/source payloads, and any compatibility notes in the parent task.
- [x] Only after this child passes its checks, hand the contracts to `p1-context-artifact-frontend`.

### 前端交接契约

- Agent ids 与 Artifact type 一一对应：`course_qa`、`personal_tutor`、`meeting_minutes`、`todo_breakdown`。
- `course_qa.data`：`answer`、`key_points`、`follow_up_questions`。
- `personal_tutor.data`：`diagnosis`、`explanation`、`mistakes`、`practice`、`follow_up_questions`。
- `meeting_minutes.data`：`topics`、`decisions[]`、`action_items[]`；决议/行动项含 `owner`、`due_date`、`evidence` 可选字段。
- `todo_breakdown.data`：`items[]`；每项含必填 `task`，以及 `owner`、`due_date`、`priority`、`evidence` 可选字段。
- 成功流继续发送 `artifact`（含 `artifact_id`、`type`、`title`、`data`）和 `done`；实际附件引用先发送为 `artifact.type = "sources"` 的 `sources[]`，只来自 `ContextBuilder` 检索结果。
- 学生无显式附件选择返回 `agent_input_incomplete`；结构化结果无效返回 `invalid_structured_output`；跨工作区显式附件在进入流前返回 HTTP 422 `attachment_selection_invalid`。
