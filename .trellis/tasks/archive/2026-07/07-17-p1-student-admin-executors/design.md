# 学生与行政 Executor 技术设计

## 1. Scope

Implement `course_qa`, `personal_tutor`, `meeting_minutes`, and `todo_breakdown` on the existing AgentSpec → ContextBuilder → AgentExecutor → AgentRun/SSE → Artifact path. No schema migration is required.

## 2. Agent contracts

Extend `AgentSpec` configuration with independent `executor_id`, prompt, `InputContract`, `ContextPolicy`, and skill ids:

| Agent | Role | Required input | Artifact type |
| --- | --- | --- | --- |
| `course_qa` | student | user content + explicitly selected course material | `course_qa` |
| `personal_tutor` | student | user content + explicitly selected mistake/assignment material | `personal_tutor` |
| `meeting_minutes` | admin | user content; optional explicitly selected meeting material | `meeting_minutes` |
| `todo_breakdown` | admin | user content; optional explicitly selected meeting/task material | `todo_breakdown` |

Use `apps/api/app/agents/student/` and `apps/api/app/agents/admin/` modules, plus a small `p1_contracts.py` module for Pydantic output models and deterministic Markdown serializers. Each Executor owns its prompt and parser even if the model-streaming helper is shared.

### Output models

- `CourseQAOutput`: `answer: str`, `key_points: list[str]`, `follow_up_questions: list[str]`.
- `PersonalTutorOutput`: `diagnosis: str`, `explanation: str`, `mistakes: list[str]`, `practice: list[str]`, `follow_up_questions: list[str]`.
- `MeetingMinutesOutput`: `topics: list[str]`, `decisions: list[Decision]`, `action_items: list[ActionItem]`; owner/date fields are optional.
- `TodoBreakdownOutput`: `items: list[TodoItem]`; `task` is required, owner/date/priority/evidence are optional.

Use `parse_json`/`TypeAdapter` without repair. Empty required strings or malformed shapes become `invalid_structured_output`. Serialize `model_dump()` into Artifact `data` and a deterministic Markdown `content`; citations are copied only from the built `AgentContext`.

## 3. ContextPolicy rules

Add a policy flag (default preserving current behavior) to distinguish whether a request with no `selected_attachment_ids` may implicitly use current conversation uploads:

- Student agents: `requires_explicit_attachments=True`, so no selected files returns `agent_input_incomplete` before retrieval/model execution.
- Admin agents: direct message content is valid with no attachment, but `allow_implicit_conversation_attachments=False`; only IDs explicitly sent by the caller enter retrieval. Selected IDs still pass workspace + current conversation ownership checks.
- All four agents set `exclude_learning_details=True`.
- Selected Artifact validation remains `ArtifactRepository.list_selected_for_conversation`; no cross-workspace or cross-conversation result can enter context.

This change must not alter generic chat or existing teacher P0 behavior unless its policy explicitly opts in.

## 4. Execution and errors

The Executor calls the existing `GenericChatExecutor` with a role-specific JSON-only system prompt. On success it returns one `AgentArtifact` with structured data, readable Markdown, citations and validation metadata. `stream_assistant_reply()` persists it and emits the existing events.

- Missing selected student material: 422 `agent_input_incomplete`, status `needs_input`, no model call.
- Invalid JSON/schema: 422 `invalid_structured_output`, no successful Artifact, retryable through the existing AgentRun flow.
- Provider failure: existing `failed` state and retry behavior.
- Admin content-only requests: no attachment retrieval unless IDs were explicitly supplied.

## 5. Test design

- Unit tests use a fake `ChatProvider` and verify prompts, structured parsing, Markdown/data shape, citations, and model-call suppression for missing input.
- API tests execute the real stream path and assert Artifact/SSE/AgentRun status.
- Isolation tests create multiple role workspaces, attempt foreign attachment/artifact ids, and assert stable 4xx errors and no foreign source in provider messages.
- Regression tests assert existing teacher executor resolution and generic/lesson/classroom behavior remain unchanged.
