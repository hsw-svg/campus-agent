# Implementation Plan: Agent Streaming Progress

## Ordered checklist

1. [x] Confirm current branch/worktree and read the frontend/backend layer specifications before editing.
2. [x] Extend the internal agent execution contract with typed status/delta/result events and normalize the backend SSE event vocabulary, including `route_decision`.
3. [x] Refactor `GenericChatExecutor` so plain model fragments can flow through the executor boundary without changing existing `execute` callers.
4. [x] Add course-iteration streaming phases and throttled safe model-generation progress; keep structured JSON private until validation and Artifact creation complete.
5. [x] Add learning-analysis streaming phases around table parsing, statistics, validation, and Artifact creation; preserve anonymous-data filtering.
6. [x] Update `stream_assistant_reply` to consume executor events, forward visible deltas immediately, serialize progress statuses, preserve final persistence, and handle fallback heartbeats/cancellation.
7. [x] Add or update backend tests for event ordering, multiple deltas, course iteration progress, learning-analysis privacy, fallback/error, and cancellation behavior.
8. [x] Add frontend progress types/reducer logic in `api.ts` and `useWorkspaceChat.ts`, keeping existing `toolStatus`, `runStatus`, route, Artifact, and resume-assistant compatibility.
9. [x] Build `AgentProgressPanel.tsx` and integrate it into the teacher course conversation and standalone teacher-agent execution view; remove/replace the old full dialogue thinking animation.
10. [x] Run focused API tests, full API tests as practical, `npm.cmd run lint`, `npm.cmd run build`, `git diff --check`, and Docker-served browser verification.
11. [ ] Run the Trellis quality check, update the relevant spec if the stable streaming contract is project-wide, then prepare a single-theme Git commit after user confirmation.

## Validation commands

```powershell
cd apps/api
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_conversations.py tests/api/test_stage5_routing.py tests/api/test_stage6_learning_analysis.py tests/agents/test_course_iteration_executor.py

cd ..\web
npm.cmd run lint
npm.cmd run build

cd ..\..
git diff --check
docker compose -f docker-compose.yml -f docker-compose.dev.yml config
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

Use the existing Docker app on port 8080 for UI verification; do not start a separate local Vite server on port 3000.

## Risk points and rollback

- Risk: forwarding deltas before final normalization can duplicate or conflict with validated Markdown. Mitigation: only specialized plain-text streams emit visible deltas; structured course output emits safe progress and one final normalized result.
- Risk: old consumers assume `tool_status.status` is a simple string. Mitigation: keep that field and add optional fields; frontend normalizes both forms.
- Risk: executor cancellation leaves a background task running. Mitigation: use shielded waits only for heartbeat fallback and explicitly cancel/await the task in the cancellation path.
- Risk: progress UI introduces a second scroll owner. Mitigation: cap the visible step list and keep the panel in the existing conversation scroll container.
- Rollback: revert the single feature commit; the existing SSE event parser and `execute` methods remain compatible, so disabling specialized `stream` dispatch returns to final-result behavior.

## Review gate before activation

- [x] `prd.md` has no unresolved product decisions and acceptance criteria map to the implementation.
- [x] `design.md` and `implement.md` describe the same event payload and structured-output policy.
- [x] No implementation begins until the task is started with `task.py start`.
