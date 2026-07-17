# Context、Artifact 与 React 工作区执行计划

## Baseline

- [x] Read the child PRD, parent design, frontend spec index, and shared cross-layer guides.
- [x] Inspect the actual React package, hook, API client, teacher resource panel, and artifact card.

## Implementation

- [x] Add a typed `SourceCitation` decoder at the SSE boundary and reset citation state with workspace/conversation context.
- [x] Add shared `ResourcePicker` grouping current attachments, workspace attachments, and selectable Artifacts.
- [x] Extend `ArtifactCard` for `course_qa`, `personal_tutor`, `meeting_minutes`, and `todo_breakdown` without changing teacher P0 renderers.
- [x] Wire student/admin workspaces to selection, citation display, copy/export, retry, stop, and responsive resource access.
- [x] Keep only explicit selected ids in the existing `streamMessage` request shape.

## Validation

- [x] `cd apps/web; npm.cmd run lint`
- [x] `cd apps/web; npm.cmd run build`
- [ ] Browser/demo smoke check when a browser runner is available.

备注：当前环境未提供可用的浏览器运行器；直接启动 Vite 的命令在本地开发服务器监听前超时且未留下监听进程，因此以 TypeScript 检查和生产构建作为可执行门禁。

## Handoff

- [x] Pass the actual UI terminology, React paths, and status/error behavior to the documentation child.

### 文档交接

- 真实前端入口仍是 `apps/web/src/App.tsx`，工作区为 `StudentWorkspace.tsx`、`AdminWorkspace.tsx`、`TeacherWorkspace.tsx`。
- 资源选择组件为 `components/ResourcePicker.tsx`；共享结果组件为 `components/ArtifactCard.tsx`；SSE 与选择状态归 `hooks/useWorkspaceChat.ts`。
- UI 文案使用“当前对话附件 / 工作区资料库 / 本次任务资料 / 本次任务成果 / 实际引用”；前端命令为 `npm.cmd run lint` 和 `npm.cmd run build`，开发端口为 3000。
