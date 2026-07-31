# Student Resume Assistant

## 1. Scope / Trigger

Use this contract when the student workspace selects a current resume, combines it with real course progress, runs `resume_helper`, or lists/deletes resume-analysis history.

## 2. Signatures

- DB: `StudentResumeProfile(workspace_id PK, current_attachment_id FK attachment.id)`.
- `GET /api/resume-assistant/profile -> { current_resume: AttachmentResponse | null }`
- `PUT /api/resume-assistant/profile { attachment_id: UUID }`
- `POST /api/resume-assistant/analyses/stream { attachment_id, target_role?, job_description?, selected_course_ids[] } -> text/event-stream`
- `GET /api/resume-assistant/analyses -> ResumeAnalysisHistoryResponse[]`
- `DELETE /api/resume-assistant/analyses/{run_id} -> 204`
- Agent: `resume_helper` produces one `resume_analysis` Artifact with schema `resume_analysis.v1`.

## 3. Contracts

- Every endpoint is student-only and workspace-scoped.
- The current resume must be a general workspace Attachment: `scope=workspace`, `conversation_id=NULL`, `course_id=NULL`, extension in `.pdf/.docx/.txt/.md`, status `indexed|degraded`, and `extracted_chars > 0`.
- Upload and analysis are separate actions. Uploading or replacing the current resume never starts a model request.
- Replacing the profile pointer does not delete prior Attachments or prior analysis history.
- Only explicitly selected, owned, started courses enter the analysis snapshot. The snapshot may contain progress percent, completed chapters/knowledge points, current chapter, and evidence-backed weak points.
- Each analysis owns one `resume_helper` Conversation and AgentRun. A successful run owns one `resume_analysis` Artifact. Deleting the history item deletes that analysis Conversation and its dependent messages/run/artifact, but not the workspace resume Attachment.
- The executor reads all chunks of the explicitly selected resume. It does not use keyword retrieval to truncate the resume.
- Artifact `data` is:

```json
{
  "schema_version": "resume_analysis.v1",
  "input": {
    "resume_attachment_id": "uuid",
    "resume_filename": "resume.pdf",
    "target_role": null,
    "job_description": null,
    "selected_courses": []
  },
  "report": {
    "overall_summary": "...",
    "issues": [],
    "section_suggestions": [],
    "course_capability_matches": [],
    "job_match": {},
    "optimized_resume_sections": [],
    "evidence_notice": "..."
  }
}
```

- `course_capability_matches[].course_name` must match a selected course snapshot. Unsupported course claims fail the run instead of being persisted.
- The first model response is parsed strictly. If it fails `resume_analysis.v1` validation, the executor makes exactly one JSON-mode correction call using the invalid response as context and instructs the model to preserve all facts and conclusions. A second invalid response fails with `invalid_structured_output`.
- The Docker Nginx proxy allows 180 seconds for API streams so one bounded correction call can complete without the proxy cutting the SSE connection.
- Missing resume facts use `待补充`; the executor must not invent projects, internships, certificates, grades, skills, duties, or metrics.
- Frontend history shows the newest six items first, can expand all, and opens the full Artifact only in the main panel.

## 4. Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Non-student workspace | `403 resume_assistant_forbidden` |
| Missing/foreign Attachment | `404 resume_attachment_not_found` |
| Conversation/course-scoped Attachment | `422 resume_attachment_invalid_scope` |
| Unsupported resume extension | `422 resume_attachment_type_invalid` |
| Empty/scanned/unparsed document | `422 resume_attachment_text_unavailable`; no model call |
| Analysis uses a replaced resume | `409 resume_attachment_not_current` |
| More than 24 selected courses | `422 resume_course_selection_too_large` |
| Missing/foreign course | `404 course_not_found` |
| Owned but unstarted course | `422 resume_course_not_started` |
| Model names an unselected course | `422 resume_analysis_evidence_invalid`; no successful Artifact |
| Model returns invalid report structure twice | `422 invalid_structured_output`; no successful Artifact |
| Missing history run or wrong agent | `404 resume_analysis_not_found` |
| Delete a running analysis | `409 resume_analysis_running` |

## 5. Good / Base / Bad Cases

- Good: upload a readable PDF, set it as current, select two started courses, receive a structured report, refresh, and reopen it from history.
- Good: replace the current resume; earlier history still opens with its original input snapshot.
- Base: analyze with no selected courses; the report succeeds and states that no course-progress evidence was used.
- Bad: treat a catalog-only, unstarted course as a learned capability.
- Bad: query all workspace AgentRuns in React and filter there.
- Bad: accept a model-produced course capability whose course name is absent from the server-built snapshot.

## 6. Tests Required

- Profile tests assert readable files can be selected and empty/foreign/wrong-scope files are rejected.
- API tests assert only selected started courses appear in the provider prompt.
- Executor tests assert strict JSON parsing, deterministic Markdown, complete draft sections, input snapshot persistence, and rejection of unselected course claims.
- History tests assert newest-first workspace+agent scoping, nullable failed Artifacts, and delete cascade while preserving the resume Attachment.
- Role isolation tests assert teacher/admin workspaces receive `resume_assistant_forbidden`.
- Frontend checks run `npm.cmd run lint` and `npm.cmd run build`.
- Migration checks run `alembic heads`, `alembic upgrade head`, and a Docker proxy smoke test through port `8080`.

## 7. Wrong vs Correct

```python
# Wrong: send every course in the workspace and trust the model to decide.
course_context = student_courses.list_summaries(workspace_id)

# Correct: validate only explicit IDs and require real progress.
course_context = [
    resume_service.course_snapshot(workspace_id, course_id)
    for course_id in selected_course_ids
]
```

```python
# Wrong: persist a course capability just because JSON schema validation passed.
output = parse_json(result.text, ResumeAnalysisOutput)

# Correct: schema validation is followed by evidence-membership validation.
output = parse_json(result.text, ResumeAnalysisOutput)
validate_course_evidence(output, controlled_input)
```
