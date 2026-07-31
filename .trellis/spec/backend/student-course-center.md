# Student Course Center

## 1. Scope / Trigger

Use this contract when a student workspace lists real courses, enters a course detail page, starts a chapter-scoped AI conversation, or records chapter completion.

## 2. Signatures

- `POST /api/courses/defaults -> list[CourseSummaryResponse]`
- `GET /api/courses/{course_id} -> CourseDetailResponse`
- `POST /api/courses/{course_id}/start -> CourseDetailResponse`
- `POST /api/courses/{course_id}/chapters/{chapter_id}/start -> CourseDetailResponse`
- `POST /api/courses/{course_id}/chapters/{chapter_id}/complete -> CourseDetailResponse`
- `POST /api/conversations` accepts nullable `course_id: UUID` and `chapter_id: UUID`.
- Storage owners: `Course.workspace_id`, `StudentCourseProgress(workspace_id, course_id)`, and `Conversation(course_id, chapter_id)`.

## 3. Contracts

- Default initialization is explicit, student-only, and idempotent by `(workspace_id, template_key)`.
- Initialization creates only missing templates. It never updates an existing template course or its chapters.
- `started` becomes true only after a start endpoint creates `StudentCourseProgress`.
- Progress equals completed chapters divided by all course chapters; opening a page or sending a message does not complete a chapter.
- A chapter is completed only through the complete endpoint. The next unfinished chapter becomes current.
- Weak points are rebuilt from structured `personal_tutor` Artifacts joined through a Conversation with the same workspace, course, and chapter.
- With no evidence Artifact, `weak_points` is `[]`; the frontend renders an empty state and must not invent recommendations.
- The frontend course context passes both `courseId` and `chapterId` to conversation creation. Course/chapter changes clear the active chat before further sends.

## 4. Validation & Error Matrix

- Non-student calls default/start/complete endpoints -> `403 student_course_center_forbidden`.
- Missing or foreign course -> `404 course_not_found`.
- Missing or foreign chapter under an owned course -> `404 course_chapter_not_found`.
- `chapter_id` without `course_id` when creating a conversation -> `422 course_required_for_chapter`.
- Chapter from another course -> `404 course_chapter_not_found`.
- No weak-point evidence -> successful response with an empty list.

## 5. Good/Base/Bad Cases

- Good: repeat default initialization returns the same six course IDs and preserves a renamed course.
- Good: a chapter conversation produces a `personal_tutor` Artifact; completing that chapter stores only its evidence-backed recommendations.
- Base: a new course is visible with `started=false` and `progress_percent=0`.
- Bad: infer completion from chat count or opening the AI workspace.
- Bad: aggregate Artifacts by workspace only; this leaks evidence across courses.

## 6. Tests Required

- Assert default initialization is idempotent, student-only, and non-overwriting.
- Assert start/continue does not reset completed chapters.
- Assert selecting and completing a chapter persists current chapter and percentage across a later GET.
- Assert conversation creation rejects missing-course and cross-course chapter IDs.
- Assert weak points include same-workspace/course/chapter evidence and exclude another course.
- Run frontend type-check/build and a Docker proxy smoke test through port `8080`.

## 7. Wrong vs Correct

```python
# Wrong: a workspace-wide Artifact query can mix unrelated learning evidence.
select(Artifact).where(Artifact.workspace_id == workspace_id)

# Correct: join the owning Conversation and constrain all learning dimensions.
select(Artifact).join(Conversation).where(
    Artifact.workspace_id == workspace_id,
    Conversation.workspace_id == workspace_id,
    Conversation.course_id == course_id,
    Conversation.chapter_id == chapter_id,
)
```
