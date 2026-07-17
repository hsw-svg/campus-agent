# Context、Artifact 与 React 工作区设计

## 1. Scope

Extend the existing React workspaces and `useWorkspaceChat` hook. The backend
contract remains the source of truth: selected attachment/artifact ids are
submitted as arrays, stream `artifact` events carry persisted result data, and
`artifact.type = "sources"` carries the actual attachment citations.

## 2. UI data flow

`listAttachments` + `listWorkspaceAttachments` → merged typed attachments →
explicit checkbox state → `streamMessage.selectedAttachmentIds`.

`listArtifacts` / stream result → typed `Artifact` data → `ArtifactCard` →
copy or `exportArtifact(format)`.

`artifact.sources` SSE event → `SourceCitation[]` in `useWorkspaceChat` → the
latest result card only. Historical results do not inherit a later task's
citations.

## 3. Components

- `ResourcePicker` owns the shared student/admin selection presentation and
  groups current-conversation attachments, workspace attachments, and prior
  artifacts.
- `ArtifactCard` keeps existing teacher P0 renderers and adds the four P1
  schemas: course QA, personal tutor, meeting minutes, and todo breakdown.
- Student and admin workspaces only wire the hook, picker, export action, retry
  status, and responsive placement; they do not calculate backend facts.

## 4. State and errors

`useWorkspaceChat` resets selections and citations on role/token change,
conversation open, and new chat. It keeps source decoding at the SSE boundary,
stores only normalized citations, and maps `needs_input` / `failed` states to
Chinese actionable messages. Export failures are local to the workspace card
and do not change AgentRun state.

No new state-management or test framework is introduced. Existing React 19,
TypeScript, Tailwind CSS, and Vite conventions remain in use.
