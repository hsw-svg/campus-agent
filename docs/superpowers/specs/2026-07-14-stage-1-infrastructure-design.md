# Stage 1 Infrastructure Design

## Goal

Deliver a runnable foundation for the anonymous-workspace campus AI assistant: a Vue/Vite project, a FastAPI service, PostgreSQL with pgvector, database migration support, service health reporting, external-service seams, and automated test commands.

## Scope

This phase establishes platform infrastructure only. It does not add authentication, users, roles stored in the database, workspaces, conversations, attachments, RAG retrieval, agent routing, or end-user pages.

## Runtime Topology

Docker Compose defines three services:

```text
web (Nginx serving Vite build) -> api (FastAPI) -> db (PostgreSQL 16 + pgvector)
```

The frontend is a buildable Vue 3 application with an empty application mount and component-test command. It makes no HTTP requests and contains no route-level page. Nginx proxies `/api/` requests to the API service for later phases.

The API starts even when the database, chat model, or embedding model is unavailable. Runtime health is queried explicitly through `GET /api/health`.

## Backend Architecture

```text
api router
  -> health service
       -> database probe (SELECT 1)
       -> ChatProvider configuration status
       -> EmbeddingProvider configuration status

core
  -> Settings, structured logging, AppError, JSON Guard

integrations
  -> OpenAI-compatible ChatProvider and EmbeddingProvider interfaces
  -> LocalObjectStorage implementation of ObjectStorage

db
  -> SQLAlchemy engine/session factory
  -> Alembic initial migration enabling pgvector
```

`Settings` reads only environment variables and supplies development-safe defaults for host, port, database URL, and local storage root. Chat and embedding configuration are independent. A provider is `configured` only when its base URL, API key, and model name are all present; health reporting does not call external model services.

The health response uses an explicit component model:

```json
{
  "status": "degraded",
  "components": {
    "database": { "status": "healthy" },
    "chat_model": { "status": "unconfigured" },
    "embedding_model": { "status": "unconfigured" }
  }
}
```

The overall status is `healthy` only when the database is reachable and both model providers are configured. It is `degraded` otherwise. Database connectivity failures are returned as component detail rather than causing an application startup failure.

## Error and Data Boundaries

`AppError` carries a stable error code, user-safe message, HTTP status, and optional details. A global FastAPI handler serializes it as one consistent error shape. `TaskError` specializes this type for future asynchronous AI operations.

`json_guard` validates a raw LLM JSON string against a caller-provided Pydantic model and raises a `TaskError` with a stable validation code when parsing or validation fails. It does not repair malformed model output in this phase.

`ObjectStorage` exposes `put`, `get`, `delete`, and `exists`. `LocalObjectStorage` resolves keys beneath the configured storage root and rejects absolute paths and parent-directory traversal. Business modules will use this abstraction instead of constructing file paths.

## Database and Migration

SQLAlchemy 2 provides the engine and session factory. Alembic configuration imports the shared metadata and creates a single initial migration that runs `CREATE EXTENSION IF NOT EXISTS vector`. It deliberately creates no tables; `anonymous_workspace` and all business records begin in Phase 2.

## Configuration and Deployment

`.env.example` documents database, storage, CORS, and independent chat/embedding settings without secrets. Compose uses environment substitution for optional LLM values and provisions a persistent PostgreSQL volume. The API Dockerfile installs Python dependencies and runs Uvicorn. The web Dockerfile builds with npm and serves the static output with Nginx.

## Test Strategy

Backend pytest tests run without a database for configuration, provider configuration state, JSON validation, error serialization, and storage traversal protection. Health endpoint tests replace the database probe with deterministic healthy and failed probes. An integration-test command is provided for an externally running Compose database, verifying the pgvector extension and Alembic upgrade.

Frontend Vitest tests prove the root application can mount. `npm run build` validates the production Vite build. No visual page, route, or API client test is introduced.

## Acceptance Criteria

- `docker compose up --build` starts database, API, and static web services.
- `alembic upgrade head` enables the `vector` database extension.
- `GET /api/health` returns readable component states and remains available when LLM settings are absent.
- The API starts with model settings absent; health reports `unconfigured` for the relevant provider.
- Local object storage rejects keys outside its configured root.
- `pytest`, the integration test command against Compose, `npm test`, and `npm run build` have documented commands.
- No account, JWT, class, enrollment, or cross-role feature is added.
