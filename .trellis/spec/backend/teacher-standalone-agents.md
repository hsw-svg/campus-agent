# Teacher Standalone Agents

## 1. Scope / Trigger

This contract applies when a teacher-facing agent can run outside a course, especially when its course-bound form normally requires selected material. It protects course workflows from accidentally inheriting the standalone empty-material exception.

## 2. Signatures

The shared policy guard is the only place that defines the exception:

```python
allows_empty_teacher_materials(
    *,
    role: str,
    agent_id: str,
    workflow_id: str | None,
    conversation_course_id: UUID | str | None,
) -> bool
```

`ContextBuilder.build(..., workflow_id: str | None = None)` applies the guard to explicit-attachment policies. The service computes the same trusted result and passes it to executors as `AgentRequest.allow_empty_materials`.

`CourseIterationExecutor.execute(request)` returns `course_iteration` for an ordinary iteration plan and `slide_deck` when `request.content` contains a slide-deck keyword.

## 3. Contracts

- The stable workflow id is `teacher-standalone-agent`.
- Empty material is allowed only for role `teacher`, agent `classroom_interaction` or `course_iteration`, that workflow id, and a persisted Conversation whose `course_id` is null.
- `learning_analysis` always requires an explicitly selected supported table.
- `course_id` supplied in a message request remains event and AgentRun metadata for backward compatibility; it is never the trust source for the empty-material decision.
- Attachment ids still pass through the existing conversation/workspace isolation checks. The workflow does not broaden readable data.
- Course-bound execution keeps the existing material requirements even if the client supplies the standalone workflow id.
- A successful ordinary standalone `course_iteration` run owns one Markdown Artifact with `type=course_iteration`; a slide-deck request owns `type=slide_deck` and keeps the registered slide schema.
- The standalone course-iteration detail consumer must accept both `course_iteration` and `slide_deck`. A historical completed run created before this contract may have only an assistant message; display that text as a legacy result without inserting a fabricated Artifact.
- A newly created standalone Conversation may temporarily have `agent_id=null` until routing completes. While an independent Agent page owns the active conversation, exclude that conversation from the generic task list by active conversation identity as well as by persisted `agent_id`.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Standalone activity, topic and objective present, no material | Run and generate the activity package. |
| Standalone course iteration, topic and objective present, no material | Run with an empty material context. |
| Ordinary course iteration model call completes | Persist a `course_iteration` Markdown Artifact and link it from AgentRun. |
| Course iteration explicitly requests PPT/slides | Persist a `slide_deck` Artifact and render it through the slide preview/export path. |
| Historical completed iteration has assistant text but no Artifact | Display the text-only legacy result; do not report an execution failure. |
| Standalone learning analysis without a table | Emit `agent_input_incomplete`; do not call the model. |
| Course-bound activity without material or learning artifact | Emit `classroom_activity_input_incomplete`. |
| Course-bound course iteration without selected material | Emit `agent_input_incomplete`. |
| Request metadata says no course but persisted Conversation has a course | Deny the exception using the persisted course id. |

## 5. Good / Base / Bad Cases

- Good: a null-course Conversation runs `course_iteration` with workflow `teacher-standalone-agent` and no attachments.
- Good: ordinary iteration advice and slide generation produce different stable Artifact types that the same independent detail page accepts.
- Base: a normal null-course chat uses workflow `standalone-task`; no material exception is granted.
- Base: a pre-fix completed run with `artifact_status=none` remains readable through its result assistant message.
- Bad: an executor derives authorization from `AgentRequest.course_id`, because that value may be client-provided metadata.
- Bad: treating `done` plus an assistant message as sufficient for a new independent course-iteration run while leaving `artifact_status=none`.
- Bad: changing the global `ContextPolicy.requires_explicit_attachments` flag for course iteration, which would weaken course-bound execution.

## 6. Tests Required

- API regressions for material-free standalone activity and course iteration must assert a successful terminal event and a model call.
- Ordinary course-iteration tests must also assert an `artifact` event, stored `type=course_iteration`, matching content, `artifact_status=completed`, and a non-null AgentRun artifact link.
- Slide-deck executor and UI checks must keep `slide_deck` in the course-iteration accepted-type set and preserve PPTX/Markdown export.
- Standalone learning analysis without a table must assert `agent_input_incomplete` and zero model calls.
- A course-bound Conversation with a forged standalone workflow must test both activity and iteration denials.
- Existing routing/stream tests must continue to assert that client course/workflow metadata is preserved in AgentRun and SSE events.
- A client-disconnected stream must transition its `AgentRun` from `running` to `failed` with a stable cancellation error code; it must not leave a permanently running no-course task.

## 7. Stream Cancellation

`stream_assistant_reply` returns a guarded async generator. The guard catches
`asyncio.CancelledError` across the entire SSE lifecycle, including the
preparation events, context construction, executor/model call, and result
persistence. When an execution run exists, it updates the run to:

```text
status      = failed
error_code  = stream_cancelled
```

The cancellation is re-raised after the status update so ASGI can finish the
disconnect normally. The database transition is best effort and must not mask
the original cancellation. This prevents browser navigation, Vite HMR, and
explicit stop actions from leaving the UI's historical independent task in an
unrecoverable `running` state.

## 8. Wrong vs Correct

### Wrong

```python
allow_empty = request.workflow_id == "teacher-standalone-agent" and request.course_id is None
```

This trusts client metadata and can turn a course-bound task into a material-free execution.

### Correct

```python
allow_empty = allows_empty_teacher_materials(
    role=role,
    agent_id=resolved_agent,
    workflow_id=workflow_id,
    conversation_course_id=conversation.course_id,
)
request = AgentRequest(course_id=course_id, allow_empty_materials=allow_empty, ...)
```

Keep public metadata compatible while deriving authorization exclusively from the server-loaded Conversation.

For result persistence, returning raw generic chat text is wrong because the independent page treats an Artifact as the durable result contract. Wrap the same text without adding a second model call:

```python
# Wrong: completed run with artifact_status=none
return await GenericChatExecutor(provider).execute(request)

# Correct: preserve text/citations and add the durable result
result = await GenericChatExecutor(provider).execute(request)
return AgentResult(
    text=result.text,
    citations=result.citations,
    artifact=AgentArtifact(
        type="course_iteration",
        title=topic,
        content=result.text,
        data={"topic": topic, "mode": "course_iteration"},
        format="markdown",
    ),
)
```
