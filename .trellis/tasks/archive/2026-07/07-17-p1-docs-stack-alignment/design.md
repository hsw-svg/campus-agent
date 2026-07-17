# 文档与实际 React 技术栈对齐设计

## 1. Evidence

- `apps/web/package.json`: React 19、Vite、TypeScript、Tailwind CSS、lucide-react、Motion；开发端口 3000；现有检查为 `npm.cmd run lint` 和 `npm.cmd run build`。
- `apps/web/src/`: `App.tsx`、三角色 `*Workspace.tsx`、`useWorkspaceChat.ts`、`api.ts`、`ArtifactCard.tsx`、`ResourcePicker.tsx`。
- `docker-compose.yml`: Web 容器对外 8080；前端容器内部仍由 Nginx 提供静态站点。
- API 使用 Fetch/SSE；状态主要由 React hooks 和组件本地 state 管理，没有 Pinia、Vue Router 或 Element Plus。

## 2. Files and policy

Update only current-stack claims in `docs/开发文档.md`、`docs/设计方案.md`、
`docs/前端开发文档.md`、`docs/UI设计提示词.md` and `AGENTS.md`. Keep product
boundaries, security constraints, and unimplemented agent scope explicit.

For the P1 status, mark the delivered first cut (student CourseQA,
PersonalTutor, admin MeetingMinutes, TodoBreakdown, selected resources, common
export/UI cards) as implemented; keep grading, course iteration, and teaching
report as later work unless code evidence says otherwise.

## 3. Verification

Search affected docs for Vue/Pinia/Element Plus/Vue Test Utils/5173, inspect
remaining matches manually, then run Markdown whitespace checks and the actual
frontend/backend validation already recorded by the child tasks.
