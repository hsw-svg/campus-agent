# P1 文档与技术栈对齐

## Goal

Update development, design, frontend, project instruction, and related docs so they describe the repository's actual implementation and the P1 contracts delivered by the parent task.

## Requirements

- Replace stale Vue 3/Pinia/Element Plus/Vue Test Utils assumptions with the current React 19, Vite, TypeScript, Tailwind CSS, lucide-react, Motion, Fetch/SSE, and existing lint/build commands where the code is authoritative.
- Correct frontend file examples, component terminology, development port (Vite 3000), Docker port (8080), and state-management guidance to match `apps/web`.
- Update architecture diagrams and stage/progress wording only where implementation evidence supports it; do not rewrite product scope or invent completed features.
- Keep P1 role boundaries, explicit resource selection, Artifact export, and no-account/no-push constraints consistent across docs.
- Preserve any existing documentation that remains accurate and record unresolved gaps instead of masking them.

## Acceptance Criteria

- [ ] `rg` finds no stale Vue/Pinia/Element Plus claims in the affected current-stack sections; any intentional historical reference is labeled.
- [ ] Docs accurately name the actual frontend commands, ports, directories, and state/API patterns.
- [ ] Docs describe the delivered P1 agents and their selection/isolation constraints without claiming unimplemented later P1 items are complete.
- [ ] Markdown diff passes `git diff --check` for the child changes.

## Notes

This child should run after the backend and frontend contracts stabilize, but the stack corrections can be prepared earlier from the repository evidence.
