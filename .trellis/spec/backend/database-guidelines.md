# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

<!--
Document your project's database conventions here.

Questions to answer:
- What ORM/query library do you use?
- How are migrations managed?
- What are the naming conventions for tables/columns?
- How do you handle transactions?
-->

(To be filled by the team)

## Scenario: Course-scoped tasks and materials

### 1. Scope / Trigger

Use this contract when a task must be grouped under a course or remain independent.

### 2. Signatures

- `Course(id, workspace_id, name, description)` is workspace-scoped.
- `Conversation.course_id` is nullable; the product calls Conversation a task.
- `Attachment.course_id` is nullable; `NULL` means workspace-generic material.

### 3. Contracts

Course tasks may read all of their course materials and generic materials by default. Independent tasks may read only
generic workspace materials plus their own conversation attachments. Course and task ownership must always include
`workspace_id`.

`AttachmentRepository.list_selected_for_conversation(workspace_id, conversation_id, attachment_ids, course_id)` keeps
the legacy explicit-selection behavior for independent tasks. When `course_id` is non-null and `attachment_ids` is
`None` or empty, it resolves the complete course-visible set (course-scoped workspace files, generic workspace files,
and current conversation uploads). This is the server-side fallback for a course task's first send.

### 4. Validation & Error Matrix

- Creating a task with another workspace's course -> `404 course_not_found`.
- Selecting another course's material -> `422 attachment_selection_invalid`.
- No course ID -> create an independent task and filter workspace materials to `course_id IS NULL`.
- Course task with no attachment IDs -> use all materials visible to that course; do not return an empty context only
  because the frontend has not finished loading the library.

### 5. Good/Base/Bad Cases

- Good: switching a course clears the active task and reloads only that course's materials.
- Good: a course task sends no explicit selection and the server resolves all materials visible to that course.
- Base: legacy tasks with `course_id = NULL` remain available as independent tasks.
- Bad: listing all workspace attachments for every course leaks teaching context.

### 6. Tests Required

- Create/list course task and independent task; assert their `course_id` values.
- Reject a course ID owned by another workspace.
- Assert course material listing excludes another course's material.
- Assert a course learning-analysis request without `selected_attachment_ids` uses the course set and excludes another
  course's table.

### 7. Wrong vs Correct

```python
# Wrong: list every workspace material for the active course.
attachments.list_workspace_for_conversation(workspace_id)

# Correct: scope generic and current-course materials.
attachments.list_workspace_for_conversation(workspace_id, conversation.course_id)

# Course task default: an empty client selection is resolved server-side.
attachments.list_selected_for_conversation(workspace_id, conversation.id, [], conversation.course_id)
```

## Scenario: AgentRun teaching workflow context

### 1. Scope / Trigger

Use this contract when a streamed agent task must remain traceable to a course and a previous teaching step
without introducing a course/account domain model.

### 2. Signatures

`POST /api/conversations/{conversation_id}/messages/stream` accepts nullable `course_id: str(96)`,
`workflow_id: str(96)`, `parent_run_id: UUID`, and at most 64 `input_refs: list[str]`.
The same fields are persisted on `AgentRun` and copied into `AgentRequest`.

### 3. Contracts

`input_refs` contains explicit opaque references such as `attachment:<uuid>` and `artifact:<uuid>`.
Retries must reuse all four fields from the existing run. `message_start` echoes course, workflow, and parent Run IDs.

### 4. Validation & Error Matrix

- Missing optional context -> create an ungrouped run for backward compatibility.
- Parent Run missing from the current workspace or conversation -> HTTP 422 `parent_run_not_found`.
- More than 64 input references or IDs longer than 96 characters -> Pydantic request validation error.

### 5. Good/Base/Bad Cases

- Good: activity-package Run references the preceding learning-analysis Run and selected analysis Artifact.
- Base: ordinary chat sends no course/workflow fields and behaves as before.
- Bad: accepting a parent Run from another conversation creates a cross-context chain and must be rejected.

### 6. Tests Required

- API test asserts `message_start.course_id` and `workflow_id` match the request.
- API test asserts a foreign/cross-conversation `parent_run_id` returns `parent_run_not_found`.
- Migration check runs `alembic upgrade head`; revision IDs must fit `alembic_version.version_num` (32 chars).

### 7. Wrong vs Correct

```python
# Wrong: trust an arbitrary client parent ID.
run_values["parent_run_id"] = parent_run_id

# Correct: scope lookup by workspace and verify the same conversation first.
parent = agent_runs.get(workspace_id, parent_run_id)
if parent is None or parent.conversation_id != conversation.id:
    raise AppError(code="parent_run_not_found", status_code=422, message="...")
```

---

## Query Patterns

<!-- How should queries be written? Batch operations? -->

(To be filled by the team)

---

## Migrations

<!-- How to create and run migrations -->

(To be filled by the team)

---

## Naming Conventions

<!-- Table names, column names, index names -->

(To be filled by the team)

---

## Common Mistakes

<!-- Database-related mistakes your team has made -->

(To be filled by the team)
