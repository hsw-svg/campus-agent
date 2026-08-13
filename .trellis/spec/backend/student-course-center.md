# Student Course Center

## 1. Scope / Trigger

Use this contract when a student workspace lists real courses, enters a course detail page, starts a chapter-scoped AI conversation, or records chapter completion.

## 2. Signatures

- `POST /api/courses/defaults -> list[CourseSummaryResponse]`
- `POST /api/courses -> CourseResponse` creates a student-owned custom course without starting it.
- `GET /api/courses/{course_id} -> CourseDetailResponse`
- `POST /api/courses/{course_id}/textbook { topic, use_course_materials } -> CourseDetailResponse`
- `POST /api/courses/{course_id}/start -> CourseDetailResponse`
- `POST /api/courses/{course_id}/chapters/{chapter_id}/start -> CourseDetailResponse`
- `POST /api/courses/{course_id}/chapters/{chapter_id}/complete -> CourseDetailResponse`
- `POST /api/conversations` accepts nullable `course_id: UUID` and `chapter_id: UUID`.
- `POST /api/conversations/{conversation_id}/messages/stream` accepts nullable `course_id: str` and `chapter_id: UUID`; bound conversations compare them with stored IDs before persisting a turn.
- `StudentCourseService.get_learning_context(workspace_id, course_id, chapter_id) -> CourseLearningContext` returns server-owned metadata for routing and prompts.
- Storage owners: `Course.workspace_id`, `StudentCourseProgress(workspace_id, course_id)`, and `Conversation(course_id, chapter_id)`.
- Textbook binding storage: `Course.deeptutor_book_id`, `CourseChapter.deeptutor_chapter_id`, and `CourseChapter.deeptutor_page_ids`.

## 3. Contracts

- Default initialization is explicit, student-only, and idempotent by `(workspace_id, template_key)`.
- Initialization creates only missing templates. It never updates an existing template course or its chapters.
- `started` becomes true only after a start endpoint creates `StudentCourseProgress`.
- Course-center listing includes templates and custom courses. Learning-center listing is a frontend projection containing only `started=true` courses; creating or binding a textbook does not start a course.
- A course textbook is created once. The service sends the course name, description, requested topic, and optionally the deterministic course knowledge-base name to DeepTutor, then validates the final book/spine before one database commit.
- Empty custom courses receive chapters from non-overview Tutor spine entries. Existing/template courses retain chapter IDs, titles, order, and progress; matching Tutor chapters bind by position and unmatched local chapters remain unbound.
- Every bound non-overview Tutor chapter requires at least one real `page_id`. A book ID without usable page mappings is invalid and must not partially bind the course.
- Progress equals completed chapters divided by all course chapters; opening a page or sending a message does not complete a chapter.
- A chapter is completed only through the complete endpoint. The next unfinished chapter becomes current.
- Weak points are rebuilt from structured `personal_tutor` Artifacts joined through a Conversation with the same workspace, course, and chapter.
- With no evidence Artifact, `weak_points` is `[]`; the frontend renders an empty state and must not invent recommendations.
- The frontend course context passes both `courseId` and `chapterId` to conversation creation. Course/chapter changes clear the active chat before further sends.
- Stream requests pass both IDs, but backend rebuilds course name, description, category, chapter summary, and knowledge points from the Conversation binding.
- `course_qa` may run without attachments when valid course metadata exists. It may explain scope and basic concepts, but cannot claim textbook quotations, pages, examples, or teacher requirements without materials.

## 4. Validation & Error Matrix

- Non-student calls default/start/complete endpoints -> `403 student_course_center_forbidden`.
- Missing or foreign course -> `404 course_not_found`.
- Missing or foreign chapter under an owned course -> `404 course_chapter_not_found`.
- `chapter_id` without `course_id` when creating a conversation -> `422 course_required_for_chapter`.
- Chapter from another course -> `404 course_chapter_not_found`.
- No weak-point evidence -> successful response with an empty list.
- Foreign course textbook request -> `404 course_not_found`.
- Course already has `deeptutor_book_id` -> `409 course_textbook_exists`.
- `use_course_materials=true` without an owned queued/syncing/ready course KB -> `409 course_materials_not_ready`.
- Tutor response lacks book ID, usable chapters, chapter IDs/titles, or page IDs -> `502 deeptutor_invalid_response`; no local binding is committed.
- Database binding fails after Tutor creation -> `500 course_textbook_binding_failed` with the created book ID in details; local transaction rolls back.
- Submitted course/chapter differs from a bound Conversation -> `422 conversation_course_context_mismatch`; no Message or AgentRun is created.

## 5. Good/Base/Bad Cases

- Good: repeat default initialization returns the same six course IDs and preserves a renamed course.
- Good: a chapter conversation produces a `personal_tutor` Artifact; completing that chapter stores only its evidence-backed recommendations.
- Base: a new course is visible with `started=false` and `progress_percent=0`.
- Good: a student uploads a course material, creates a textbook with that course KB, receives real Tutor page mappings, then starts the course and selects a generated chapter.
- Good: binding a Tutor book to a started template course preserves completed chapters and progress.
- Base: a topic-only custom course can create a textbook without materials; chat still uses stored course/chapter metadata.
- Bad: mark a course started when it is merely created or receives a textbook.
- Bad: replace template chapters from Tutor and thereby invalidate progress/conversation foreign keys.
- Bad: infer completion from chat count or opening the AI workspace.
- Bad: aggregate Artifacts by workspace only; this leaks evidence across courses.

## 6. Tests Required

- Assert default initialization is idempotent, student-only, and non-overwriting.
- Assert start/continue does not reset completed chapters.
- Assert selecting and completing a chapter persists current chapter and percentage across a later GET.
- Assert conversation creation rejects missing-course and cross-course chapter IDs.
- Assert stream mismatch is rejected before model execution and injected metadata belongs only to the bound course/chapter.
- Assert `course_qa` works without a textbook when course metadata exists, while unbound course QA still requires material.
- Assert topic-only and material-KB textbook creation, duplicate rejection, final page mapping, and all-or-nothing invalid-response handling.
- Assert an empty custom course receives Tutor chapters while an existing template preserves chapter identity and completion state.
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

```python
# Wrong: frontend display text becomes model truth.
course_name = payload.course_name

# Correct: stored IDs select server-owned facts.
course_context = student_courses.get_learning_context(
    workspace.id, conversation.course_id, conversation.chapter_id
)
```

```python
# Wrong: bind the pre-compilation spine, whose page_ids may still be empty.
course.deeptutor_book_id = proposal["book"]["id"]

# Correct: validate the post-confirmation spine, then persist book/chapter/page IDs together.
book_id, chapters = parse_created_textbook(result)
service._bind_textbook(course, book_id, chapters)
session.commit()
```
