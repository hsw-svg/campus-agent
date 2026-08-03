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
Invoke-RestMethod http://localhost:8080/api/health
docker compose down
```

Compose production mode runs one `app` container containing the React static build, Nginx, the FastAPI backend, and DeepTutor. The browser uses `http://localhost:8080`; FastAPI reaches DeepTutor at `127.0.0.1:8001` inside the container, and port 8001 is not published. `GET /api/health` reports database, model, and (when enabled) DeepTutor component status. `start.cmd` remains the lightweight two-process local React/API development launcher.

### DeepTutor 演示部署

DeepTutor is pinned to `1.5.8` and installed in `/opt/deeptutor-venv`, separate from the API environment. Its books, knowledge bases, and sessions are stored under `/app/runtime/deeptutor-data` and persisted by the `deeptutor_data` Compose volume. The entrypoint waits for the DeepTutor book health endpoint before starting FastAPI, then serves the React build through Nginx.

The container maps `CHAT_BASE_URL`/`CHAT_API_KEY`/`CHAT_MODEL` to DeepTutor's `LLM_*` variables. Existing embedding variables are reused, with `DEEPTUTOR_EMBEDDING_HOST` available for a provider that requires a full `/embeddings` endpoint and `DEEPTUTOR_EMBEDDING_DIMENSION` available for an explicit vector size. Changing the embedding model or dimension requires rebuilding the DeepTutor knowledge base. Prepare the main interactive books before the event because the same API key shares quota and rate limits with the existing application.

Only the current application origin exposes `/api/deeptutor/*`; the browser never calls DeepTutor directly. If the DeepTutor dependency is unavailable, the main API remains readable with a degraded health component, while the Compose container fails its full readiness healthcheck.

## Repository Map

- `apps/web`: React/Vite application, visual workspaces, API client, and SSE chat integration.
- `apps/api`: FastAPI service, database migration, integrations, and tests.
- `infra`: Docker, Nginx, PostgreSQL, and pgvector deployment assets.
- `docs`: Product design, architecture guidance, and implementation plans.
- `storage`: Git-ignored runtime root for local object storage.
