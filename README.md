# Campus Agent

An anonymous-workspace campus AI assistant with separate student, teacher, and administrative workspaces.

## Repository Map

- `apps/web`: Vue 3 conversation workbench.
- `apps/api`: FastAPI service and workspace-scoped business domains.
- `packages/contracts`: Shared API, SSE, and structured agent-result contracts.
- `packages/config`: Shared project conventions and quality configuration.
- `infra`: Docker, Nginx, PostgreSQL, and pgvector deployment assets.
- `docs`: Product design, architecture guidance, and implementation plans.
- `scripts`: Bootstrap, migration, and demonstration scripts.
- `storage`: Git-ignored runtime root for local object storage.
