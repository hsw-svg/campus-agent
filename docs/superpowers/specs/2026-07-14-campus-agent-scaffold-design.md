# Campus Agent Project Scaffold Design

## Goal

Create a monorepo directory scaffold for all eleven delivery phases in the campus AI assistant design. The structure supports a Vue 3 client, FastAPI service, PostgreSQL with pgvector, local object storage, Docker Compose deployment, and strict anonymous-workspace isolation.

## Scope

This work creates directories and lightweight placement markers only. It does not implement APIs, database models, pages, LLM calls, storage operations, or deployment behavior.

## Repository Layout

```text
apps/
  web/                              Vue 3 application
    src/
      api/                          HTTP and SSE clients
      components/                   Reusable UI components
      composables/                  Reusable Vue composition logic
      modules/                      Feature modules
      router/                       Client-side routes
      stores/                       Pinia stores
      views/                        Route-level screens
  api/                              FastAPI application
    app/
      api/                          HTTP endpoints and request dependencies
      core/                         Settings, logging, errors, JSON validation
      db/                           SQLAlchemy session and migration support
      domains/                      Workspace-scoped business domains
      integrations/                 LLM, embedding, storage, parsing adapters
      tests/                        Unit and integration tests
packages/
  contracts/                        Shared API, SSE, and agent contracts
  config/                           Shared project-quality configuration
infra/
  docker/                           API, web, and Nginx container definitions
  postgres/                         PostgreSQL and pgvector initialization
scripts/                            Bootstrap, migration, and demo-data scripts
storage/                            Git-ignored local object-storage runtime data
docs/
  architecture/                     Architecture and isolation conventions
```

## Domain Boundaries

The backend `domains/` directory contains independent modules for `workspaces`, `conversations`, `attachments`, `rag`, `agents`, `artifacts`, and `teacher_interactions`. Each domain will own its API schemas, models, repositories, services, and tests as implementation begins.

The frontend `modules/` directory mirrors the user-facing capabilities: `workspace`, `conversation`, `attachment`, `agent`, and `artifact`. The web client has one shared conversation workbench, with role-specific capabilities determined by the current anonymous workspace rather than separately deployed role applications.

## Isolation Rules

- No directory or module represents users, accounts, logins, JWT, classes, enrollment, or student-teacher relationships.
- Every domain resource will carry and be accessed through `workspace_id`.
- Repository interfaces will require a workspace scope for resource queries; ID-only resource lookup is prohibited.
- Role-specific agents will be registered behind a role-filtered whitelist in `domains/agents`.
- Object storage integrations will receive a workspace namespace, never construct raw paths in business code.
- Cross-role data transfer, implicit context reuse, and role-specific shared data stores are out of scope.

## Phase Coverage

| Phase | Scaffold location |
| --- | --- |
| 1. Infrastructure | `apps/`, `packages/config/`, `infra/`, `scripts/` |
| 2. Anonymous workspaces | `apps/api/app/domains/workspaces/`, `apps/web/src/modules/workspace/` |
| 3. Conversation shell | `domains/conversations/`, `web/src/modules/conversation/`, `views/`, `stores/` |
| 4. Attachments and RAG | `domains/attachments/`, `domains/rag/`, matching web modules |
| 5. Agent routing | `domains/agents/`, `web/src/modules/agent/`, `packages/contracts/` |
| 6-7. Teacher capabilities | `domains/teacher_interactions/`, `domains/agents/` |
| 8. Student capabilities | `domains/agents/` with role-scoped implementations |
| 9. Administrative capabilities | `domains/agents/` with role-scoped implementations |
| 10. Lifecycle and isolation | `domains/`, `integrations/storage/`, `tests/`, `docs/architecture/` |
| 11. Deployment and demo | `infra/`, `scripts/`, root deployment files |

## Validation

- The tree contains placement markers for every directory described above.
- Root-level ignore rules exclude runtime storage, environment secrets, dependency caches, test artifacts, and build artifacts.
- No prohibited account or cross-role module is scaffolded.
- A recursive directory listing can verify that each documented phase has a corresponding home.

## Non-Goals

- Generating framework boilerplate or installing dependencies.
- Creating executable source files, migrations, tests, or Docker configuration.
- Initializing a Git repository. The current workspace is not a Git repository, so this design cannot be committed at this stage.
