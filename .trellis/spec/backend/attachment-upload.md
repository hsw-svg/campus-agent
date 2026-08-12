# Attachment Upload Contract

## Scenario: Course library direct upload

### 1. Scope / Trigger

Use this contract whenever a workspace or course library accepts a document upload. The upload must reuse the workspace attachment pipeline, preserve course isolation, and avoid creating a conversation solely to obtain an upload target.

### 2. Signatures

- API: `POST /api/workspaces/current/attachments?course_id=<uuid>`
- Request body: `multipart/form-data` with one `file` part.
- Frontend API: `uploadWorkspaceAttachment(token: string, file: File, courseId?: string | null): Promise<Attachment>`
- Workspace hook: `uploadFile(file: File, scope?: 'conversation' | 'workspace', workspaceCourseId?: string | null): Promise<Attachment | null>`
- DeepTutor adapter: `sync_course_material(course_id, filename, content, content_type) -> { knowledge_base_name, task_id, operation }`.
- Attachment DB/API adds nullable `knowledge_base_name`, `knowledge_base_status`, `knowledge_base_task_id`, and `knowledge_base_message`.

A course-library caller passes `scope='workspace'` and snapshots the current course ID into `workspaceCourseId` before starting the asynchronous upload.

### 3. Contracts

- `course_id` is optional for general workspace material and required for a course-library upload.
- The authenticated workspace must own the supplied course. The created attachment has `scope='workspace'`, `conversation_id=null`, and the supplied `course_id`.
- Supported extensions are `.txt`, `.md`, `.docx`, `.pdf`, `.xlsx`, and `.csv`; frontend file inputs must advertise exactly this set.
- Maximum payload size is `25 * 1024 * 1024` bytes.
- The endpoint returns `201` with `AttachmentResponse`. Parsing or storage can still produce an attachment whose `status` is `failed`; the UI must not describe that state as a successful upload.
- A successful response is merged into visible React state only if the snapshotted target course is still current. This prevents a late response from appearing in another course.
- Student textbooks are course-scoped workspace uploads. After local parsing, stable KB name is `campus-course-{course UUID without hyphens}`; first file uses multipart `/api/v1/knowledge/create`, later files use `/{kb_name}/upload`.
- Local parsing status and external KB status are separate. DeepTutor failure never rolls back stored content or MaterialChunks; accepted work stores `queued` and a task ID.

### 4. Validation & Error Matrix

| Condition | Result |
|---|---|
| Missing or unsupported extension | `400`, `unsupported_attachment_type`, including `supported_extensions` |
| File exceeds 25 MB | `413`, `attachment_too_large`; no attachment record or object is created |
| Course is absent from or owned by another workspace | `404`, `course_not_found` |
| Object storage fails after record creation | `201` attachment with `status='failed'` and a visible `status_message` |
| Parsing cannot complete | Attachment status/message from the shared processing pipeline; UI surfaces the returned state |
| DeepTutor disabled/unavailable | Local attachment remains usable; KB status is `unavailable` with fallback text |
| DeepTutor rejects create/upload | Local attachment remains usable; KB status is `failed` |
| DeepTutor accepts background task | KB status is `queued`; stable name and task ID persist |

Filename and size validation must run before `attachments.create(...)` and `storage.put(...)` so rejected files leave no database or storage residue.

### 5. Good / Base / Bad Cases

- Good: upload `scores.csv` to an owned course; it appears immediately in that course and does not create a conversation.
- Base: upload `notes.md` without `course_id`; it becomes general workspace material.
- Bad: upload `legacy.xls` or a file larger than 25 MB; reject it without adding a library entry.
- Concurrency case: begin an upload in course A, switch to course B, then receive the response; the attachment remains stored for A but is not merged into B's view.
- Good: first textbook creates a KB and the second appends to the same stable name.
- Base: local parsing succeeds while DeepTutor is unavailable; local course retrieval still works.
- Bad: set local `Attachment.status='failed'` only because external KB sync failed.

### 6. Tests Required

- API test: supported course upload returns `201`, has the requested `course_id`, and leaves `/api/conversations` empty.
- API test: unsupported extension returns the stable `400` error and the course listing stays empty.
- API test: oversized content returns `413` and the course listing stays empty.
- API test: another workspace's course returns `404` for both listing and upload.
- API test: course listings exclude attachments belonging to other courses.
- Frontend checks: `npm.cmd run lint` and `npm.cmd run build`.
- Browser regression: upload from the course library, verify loading/disabled and final status feedback, switch courses during upload, and verify no cross-course item flashes in the UI.
- Integration test inspects multipart create/append paths and requires returned task ID.
- API test persists course/scope/KB fields and lists them again for the same course.

### 7. Wrong vs Correct

#### Wrong

```ts
await uploadFile(file, 'workspace', courseContext.courseId)
setVisibleAttachments((items) => [...items, attachment])
```

This reads mutable course state around an asynchronous request and can merge a course A response into course B.

#### Correct

```ts
const uploadCourseId = courseContext.courseId
const attachment = await uploadFile(file, 'workspace', uploadCourseId)
if (uploadCourseId === courseContext.courseId && attachment) {
  showReturnedStatus(attachment)
}
```

The hook also compares the target against its current-course ref before merging the returned attachment into state.

```python
# Wrong: one field mixes independent pipelines.
attachment.status = "failed"  # only DeepTutor failed

# Correct: local retrieval stays usable.
attachment.knowledge_base_status = "unavailable"
```
