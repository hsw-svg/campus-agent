# 文档与实际 React 技术栈对齐执行计划

## Baseline

- [x] Read the child PRD, parent design, actual package scripts, Docker ports, and affected docs.
- [x] Search stale stack terms and record current code paths before editing.

## Documentation changes

- [x] Update development and design architecture docs with React/Vite/Fetch/SSE facts and delivered P1 status.
- [x] Rewrite the frontend guide's framework examples and commands using actual `.tsx`, hooks, Tailwind, and Vite paths.
- [x] Update UI prompt and `AGENTS.md` to use actual component/style terminology.
- [x] Preserve future scope and explicitly label unresolved browser smoke / later P1 gaps.

## Validation

- [x] Search affected docs for stale stack claims and review intentional historical matches; no stale Vue-era stack claims remain.
- [x] Run `git diff --check` and Trellis task validation.

## Implementation notes

- Updated `docs/开发文档.md`, `docs/设计方案.md`, `docs/前端开发文档.md`, `docs/UI设计提示词.md`, and `AGENTS.md` to describe the actual React 19/Vite/Tailwind/Hooks/Fetch-SSE stack.
- Documented the delivered student/admin P1 executors, explicit resource selection, source citations, structured Artifact cards, and Markdown/CSV export.
- Browser smoke remains an environment follow-up because no usable browser runner or stable Vite listener was available during validation.
