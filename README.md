# Campus Agent

An anonymous-workspace campus AI assistant. The active web client is the React/Vite application in `apps/web`; it uses the FastAPI service for anonymous workspaces, conversations, streaming replies, and attachments.

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
npm.cmd install --prefix apps/web
npm.cmd run lint --prefix apps/web
npm.cmd run build --prefix apps/web
```

Copy `.env.example` to `.env` before local Compose startup when you need custom values. Chat and embedding settings are deliberately independent and optional; leaving either blank does not stop the API. Their state is exposed by the health endpoint.

```powershell
docker compose up --build -d
Invoke-RestMethod http://localhost:8000/api/health
docker compose down
```

The React web application is served at `http://localhost:3000`; the API is exposed at `http://localhost:8000`. `GET /api/health` reports database, chat-model, and embedding-model component status. `start.cmd` starts both services using these defaults.

## Repository Map

- `apps/web`: React/Vite application, visual workspaces, API client, and SSE chat integration.
- `apps/api`: FastAPI service, database migration, integrations, and tests.
- `infra`: Docker, Nginx, PostgreSQL, and pgvector deployment assets.
- `docs`: Product design, architecture guidance, and implementation plans.
- `storage`: Git-ignored runtime root for local object storage.
