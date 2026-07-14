# Campus Agent

An anonymous-workspace campus AI assistant. Stage 1 provides only the runtime foundation: a Vue build, FastAPI health service, PostgreSQL with pgvector, migration support, local object storage, and test commands. It intentionally contains no account, login, JWT, class, workspace, conversation, or cross-role business feature.

## Local Development

Prerequisites: Python 3.11 or later, Node.js 20 or later, Docker Compose, and a PostgreSQL instance with pgvector for integration tests. The repository supports `uv` for Python environment management.

```powershell
cd apps/api
uv sync --extra dev
uv run pytest
uv run pytest -m integration tests/integration
uv run alembic upgrade head
```

```powershell
cd apps/web
npm.cmd install
npm.cmd run test:run
npm.cmd run build
```

Copy `.env.example` to `.env` before local Compose startup when you need custom values. Chat and embedding settings are deliberately independent and optional; leaving either blank does not stop the API. Their state is exposed by the health endpoint.

```powershell
docker compose up --build -d
Invoke-RestMethod http://localhost:8000/api/health
docker compose down
```

The web application is served at `http://localhost:8080`; the API is exposed at `http://localhost:8000`. `GET /api/health` reports database, chat-model, and embedding-model component status.

## Repository Map

- `apps/web`: Vue 3 application build and component tests.
- `apps/api`: FastAPI service, database migration, integrations, and tests.
- `infra`: Docker, Nginx, PostgreSQL, and pgvector deployment assets.
- `docs`: Product design, architecture guidance, and implementation plans.
- `storage`: Git-ignored runtime root for local object storage.
