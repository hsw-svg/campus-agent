# P1 Context、Artifact 与前端资料展示

## Goal

Complete the React workspaces' current-task context selection and P1 result presentation on top of the backend contracts, while preserving the existing visual workspaces and SSE hook.

## Requirements

- Distinguish workspace attachments, current-conversation attachments, selected task attachments, and selected task Artifacts in the UI; only selected ids may be sent in `streamMessage`.
- Wire student and admin workspaces to select attachments/Artifacts, show actual citations/results returned by the current Executor, and reset selections when creating/opening/switching conversations or roles.
- Render the four P1 Artifact types in readable structured cards with copy and common Markdown/CSV export actions; show missing-input, failed, retryable, and degraded states with actionable Chinese messages.
- Reuse the existing React 19/Vite/Tailwind/TypeScript components and `useWorkspaceChat`; do not implement the Vue/Pinia/Element Plus design described by stale documents.
- Validate with the existing frontend commands (`npm run lint`, `npm run build`) and a browser/demo smoke path when available; do not add a new test framework solely to satisfy stale Vue documentation.

## Dependencies and Constraints

- Depends on the backend child for the stable P1 agent ids, Artifact types, structured data fields, and SSE payloads.
- The API already accepts `selected_attachment_ids` and `selected_artifact_ids`; change the contract only if repository evidence shows a missing field.
- Do not calculate scores, ratios, permissions, or source eligibility in React.

## Acceptance Criteria

- [ ] Student and admin screens expose explicit resource selection and send only selected ids; new conversations start with no inherited selection.
- [ ] P1 results, citations, export actions, and retry/input errors are visible in the appropriate React workspaces without fake hard-coded business results replacing the API response.
- [ ] Teacher P0 interaction remains buildable and its existing context/artifact controls continue to work.
- [ ] `npm run lint` and `npm run build` pass from `apps/web`.

## Notes

The current package has no Vitest/test script; this child uses the repository's actual TypeScript and build checks plus browser/demo smoke rather than inventing a Vue test stack.
