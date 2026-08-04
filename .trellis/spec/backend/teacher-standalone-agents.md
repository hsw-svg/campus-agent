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

## 3. Contracts

- The stable workflow id is `teacher-standalone-agent`.
- Empty material is allowed only for role `teacher`, agent `classroom_interaction` or `course_iteration`, that workflow id, and a persisted Conversation whose `course_id` is null.
- `learning_analysis` always requires an explicitly selected supported table.
- `course_id` supplied in a message request remains event and AgentRun metadata for backward compatibility; it is never the trust source for the empty-material decision.
- Attachment ids still pass through the existing conversation/workspace isolation checks. The workflow does not broaden readable data.
- Course-bound execution keeps the existing material requirements even if the client supplies the standalone workflow id.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Standalone activity, topic and objective present, no material | Run and generate the activity package. |
| Standalone course iteration, topic and objective present, no material | Run with an empty material context. |
| Standalone learning analysis without a table | Emit `agent_input_incomplete`; do not call the model. |
| Course-bound activity without material or learning artifact | Emit `classroom_activity_input_incomplete`. |
| Course-bound course iteration without selected material | Emit `agent_input_incomplete`. |
| Request metadata says no course but persisted Conversation has a course | Deny the exception using the persisted course id. |

## 5. Good / Base / Bad Cases

- Good: a null-course Conversation runs `course_iteration` with workflow `teacher-standalone-agent` and no attachments.
- Base: a normal null-course chat uses workflow `standalone-task`; no material exception is granted.
- Bad: an executor derives authorization from `AgentRequest.course_id`, because that value may be client-provided metadata.
- Bad: changing the global `ContextPolicy.requires_explicit_attachments` flag for course iteration, which would weaken course-bound execution.

## 6. Tests Required

- API regressions for material-free standalone activity and course iteration must assert a successful terminal event and a model call.
- Standalone learning analysis without a table must assert `agent_input_incomplete` and zero model calls.
- A course-bound Conversation with a forged standalone workflow must test both activity and iteration denials.
- Existing routing/stream tests must continue to assert that client course/workflow metadata is preserved in AgentRun and SSE events.

## 7. Wrong vs Correct

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
