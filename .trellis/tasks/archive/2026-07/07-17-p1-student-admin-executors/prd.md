# P1 学生与行政 Executor

## Goal

Implement the first four P1 business Executors on the existing FastAPI AgentRun/SSE pipeline without changing workspace identity or introducing accounts.

## Requirements

- Add independent AgentSpec configuration, prompts, input contracts, ContextPolicies, and Executor resolution for `course_qa`, `personal_tutor`, `meeting_minutes`, and `todo_breakdown`.
- Course QA must require explicitly selected, current-student-workspace course materials; personal tutoring must use only explicitly selected student mistakes, assignments, or self-described weak points.
- Meeting minutes and todo breakdown must use the current-admin workspace plus explicit selected materials when present; typed meeting/task content remains valid direct input, and no notification publishing or cross-role push is added.
- Parse model JSON through deterministic schemas; invalid output becomes a typed error, while successful results persist a structured Artifact with citations and stable exportable data.
- Keep deterministic facts and validation in Python; the model may organize/explain content but may not invent unsupported owners, dates, decisions, scores, or source facts.
- Add unit/API/isolation coverage for success, missing input, invalid structured output, retryable failure, citations, role allowlists, and cross-workspace selection rejection.

## Dependencies and Constraints

- Reuse the existing `AgentRequest`, `AgentResult`, `ContextBuilder`, `ArtifactRepository`, `GenericChatExecutor`, and stream protocol.
- Do not add LangChain/LangGraph to the public contract, user accounts, new identity tables, or cross-role resource relationships.
- The parent task's shared frontend and documentation children consume the stable agent ids, artifact types, and structured data fields produced here.

## Acceptance Criteria

- [ ] Each of the four agent ids resolves to a dedicated Executor and has a non-generic AgentSpec prompt, input contract, and context policy.
- [ ] Student agents cannot select or retrieve teacher/admin resources; explicit attachment/artifact ownership violations return a workspace-scoped error.
- [ ] Admin meeting minutes produce structured agenda/decisions/owners/todos output; todo breakdown produces structured actionable items and can export CSV through the common Artifact endpoint.
- [ ] All four agents produce a persisted Artifact with citations limited to ContextBuilder output and can run without a real model key under fake-provider tests.
- [ ] `uv run --extra dev python -m pytest -q` passes for the changed backend scope, or any environment-only failure is recorded.

## Notes

This child must be started after its design and implementation checklist are reviewed. The frontend child depends on the final artifact types and data shape from this child.
