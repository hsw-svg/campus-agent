# Stage 1 Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the runnable Vue, FastAPI, PostgreSQL/pgvector, migration, health-reporting, provider, storage, and test foundation described by Stage 1.

**Architecture:** The API uses small platform modules for configuration, failures, JSON validation, database access, health evaluation, and adapters. The Vue application is a buildable empty mount; Compose packages web, API, and PostgreSQL while keeping model services optional.

**Tech Stack:** Python 3.11, FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, pytest, PostgreSQL 16 + pgvector, Vue 3, Vite, TypeScript, Vitest, Nginx, Docker Compose.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `apps/api/pyproject.toml` | API runtime, test, lint, and integration-test dependencies and commands. |
| `apps/api/app/core/` | Settings, errors, logging, and JSON output validation. |
| `apps/api/app/db/` | Engine/session lifecycle and Alembic metadata. |
| `apps/api/app/services/` | Health evaluation independent of HTTP transport. |
| `apps/api/app/integrations/` | Provider contracts and local storage implementation. |
| `apps/api/app/api/` | Application factory, health router, and error handler registration. |
| `apps/api/tests/` | Unit and integration tests. |
| `apps/web/` | Buildable empty Vue root with Vitest. |
| `infra/docker/` | API, web, and Nginx Docker assets. |
| `infra/postgres/` | Database initialization assets. |
| `docker-compose.yml` | Three-service local deployment. |

### Task 1: Establish backend tooling and the test harness

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/pytest.ini`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/tests/__init__.py`

- [ ] **Step 1: Define the API project dependencies and commands**

Create `apps/api/pyproject.toml` with Python `>=3.11`, runtime dependencies `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `sqlalchemy`, `alembic`, `psycopg[binary]`, `httpx`, `openai`, `python-multipart`, and test dependencies `pytest`, `pytest-cov`, and `pytest-asyncio`. Define `pytest` as the standard unit-test command and `pytest -m integration` as the database integration-test command.

- [ ] **Step 2: Write the failing test-configuration assertion**

Create `apps/api/tests/test_project_config.py`:

```python
from pathlib import Path


def test_pyproject_declares_pytest_and_integration_marker() -> None:
    content = Path(__file__).parents[1].joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert "pytest" in content
    assert "integration" in content
```

- [ ] **Step 3: Run the test to confirm the missing project configuration fails**

Run: `cd apps/api; python -m pytest tests/test_project_config.py -q`

Expected: FAIL because `pyproject.toml` or pytest is unavailable.

- [ ] **Step 4: Add the project configuration and run the test**

Run: `cd apps/api; python -m pytest tests/test_project_config.py -q`

Expected: PASS after dependencies are installed in `.venv` using `python -m venv .venv` and `.venv\\Scripts\\python -m pip install -e ".[dev]"`.

### Task 2: Implement configuration, errors, and JSON validation

**Files:**
- Create: `apps/api/app/core/config.py`
- Create: `apps/api/app/core/errors.py`
- Create: `apps/api/app/core/json_guard.py`
- Create: `apps/api/tests/core/test_config.py`
- Create: `apps/api/tests/core/test_errors.py`
- Create: `apps/api/tests/core/test_json_guard.py`

- [ ] **Step 1: Write failing core behavior tests**

Create tests proving that absent chat or embedding environment variables produce an unconfigured provider, malformed JSON raises `TaskError(code="invalid_structured_output")`, and an `AppError` serializes `code`, `message`, and `details`.

```python
def test_invalid_json_raises_a_stable_task_error() -> None:
    with pytest.raises(TaskError, match="invalid_structured_output"):
        parse_json("not-json", Answer)
```

- [ ] **Step 2: Run the core tests and confirm they fail for missing modules**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests/core -q`

Expected: FAIL with module import errors for `app.core` implementations.

- [ ] **Step 3: Add minimal core implementations**

Implement `Settings(BaseSettings)` with database URL, local storage root, CORS origins, and separate `CHAT_*` / `EMBEDDING_*` settings. Implement `AppError`, `TaskError`, and `parse_json(raw: str, model: type[T]) -> T` using `pydantic.TypeAdapter`.

- [ ] **Step 4: Run the core tests**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests/core -q`

Expected: PASS.

### Task 3: Implement adapter contracts and safe local storage

**Files:**
- Create: `apps/api/app/integrations/llm/providers.py`
- Create: `apps/api/app/integrations/embedding/providers.py`
- Create: `apps/api/app/integrations/storage/base.py`
- Create: `apps/api/app/integrations/storage/local.py`
- Create: `apps/api/tests/integrations/test_providers.py`
- Create: `apps/api/tests/integrations/test_local_storage.py`

- [ ] **Step 1: Write failing provider and storage tests**

Test that each provider reports configured only when base URL, API key, and model are nonempty. Test that `LocalObjectStorage.put("workspace/a.txt", b"x")` round-trips data and that `get("../secret")` and `put("C:/outside.txt", b"x")` raise `AppError(code="invalid_storage_key")`.

- [ ] **Step 2: Run adapter tests to verify the missing contracts fail**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests/integrations -q`

Expected: FAIL with imports missing.

- [ ] **Step 3: Add provider protocols and `LocalObjectStorage`**

Define `ChatProvider` and `EmbeddingProvider` protocols with `is_configured` properties. Define `ObjectStorage` with `put`, `get`, `delete`, and `exists`. Resolve each local key using `Path.resolve()` and require that the resolved path remains under the configured root.

- [ ] **Step 4: Run adapter tests**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests/integrations -q`

Expected: PASS.

### Task 4: Add database lifecycle, health API, and initial migration

**Files:**
- Create: `apps/api/app/db/session.py`
- Create: `apps/api/app/db/base.py`
- Create: `apps/api/app/services/health.py`
- Create: `apps/api/app/api/health.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/0001_enable_pgvector.py`
- Create: `apps/api/tests/api/test_health.py`
- Create: `apps/api/tests/integration/test_pgvector_migration.py`

- [ ] **Step 1: Write failing health endpoint tests**

Test `GET /api/health` with injected healthy and failed database probes. Assert `database.status`, `chat_model.status`, `embedding_model.status`, and top-level `status`; a failed probe must return HTTP 200 with `status="degraded"` and an error detail.

- [ ] **Step 2: Run health tests and verify they fail**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests/api/test_health.py -q`

Expected: FAIL because the FastAPI application factory and health service are absent.

- [ ] **Step 3: Implement the health service and application factory**

Use `SELECT 1` through SQLAlchemy for the default database probe. Inject the probe and providers through `app.state` for deterministic tests. Return `healthy` only when database, chat, and embedding are all healthy/configured; map `AppError` to `{ "error": { "code", "message", "details" } }`.

- [ ] **Step 4: Add Alembic initial migration and integration test**

The migration upgrade executes `CREATE EXTENSION IF NOT EXISTS vector`; downgrade executes `DROP EXTENSION IF EXISTS vector`. Mark the migration test with `@pytest.mark.integration`, run `alembic upgrade head`, and query `pg_extension` for `vector`.

- [ ] **Step 5: Run unit and integration verification**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests -m "not integration" -q`

Expected: PASS.

Run: `docker compose up -d db; cd apps/api; .venv\\Scripts\\python -m pytest tests/integration -m integration -q`

Expected: PASS after the database becomes healthy.

### Task 5: Add the minimal Vue/Vite project and component test command

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.ts`
- Create: `apps/web/src/App.vue`
- Create: `apps/web/src/App.spec.ts`

- [ ] **Step 1: Define Vite, Vue, TypeScript, and Vitest dependencies**

Create `package.json` scripts: `dev`, `build`, `test`, and `test:run`. Use Vue 3, Vite, TypeScript, Vitest, `@vitejs/plugin-vue`, `@vue/test-utils`, and jsdom.

- [ ] **Step 2: Write the failing root mount test**

Create `App.spec.ts`:

```typescript
import { mount } from '@vue/test-utils'
import App from './App.vue'

it('mounts the application root', () => {
  expect(mount(App).exists()).toBe(true)
})
```

- [ ] **Step 3: Run the test and confirm it fails before `App.vue` exists**

Run: `cd apps/web; npm test -- --run`

Expected: FAIL because the component is missing.

- [ ] **Step 4: Add an empty accessible root component and build configuration**

Implement `App.vue` with `<main aria-label="Campus Agent"></main>` and mount it from `main.ts`. Configure Vitest for jsdom and Vue transforms without adding routes or API calls.

- [ ] **Step 5: Run frontend test and production build**

Run: `cd apps/web; npm test -- --run; npm run build`

Expected: Both commands PASS.

### Task 6: Containerize the stack, document local setup, and verify it

**Files:**
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `infra/docker/api.Dockerfile`
- Create: `infra/docker/web.Dockerfile`
- Create: `infra/docker/nginx.conf`
- Create: `infra/postgres/init.sql`
- Modify: `README.md`

- [ ] **Step 1: Write a failing Compose-structure test**

Create `apps/api/tests/test_compose_config.py` asserting that the root Compose file names `db`, `api`, and `web`, and that `.env.example` contains independent `CHAT_MODEL` and `EMBEDDING_MODEL` keys.

- [ ] **Step 2: Run the Compose-structure test and verify it fails**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests/test_compose_config.py -q`

Expected: FAIL because Compose and environment templates are absent.

- [ ] **Step 3: Add Docker and environment configuration**

Compose uses `pgvector/pgvector:pg16`, a named database volume, database health checks, and API dependency on database health. Nginx serves the built client and proxies `/api/` to `api:8000`. The README documents virtual-environment setup, npm install, test/build commands, Compose startup, migration, and the health endpoint.

- [ ] **Step 4: Run the complete verification sequence**

Run: `cd apps/api; .venv\\Scripts\\python -m pytest tests -q`

Expected: PASS with integration tests skipped unless explicitly selected.

Run: `cd apps/web; npm test -- --run; npm run build`

Expected: PASS.

Run: `docker compose up --build -d; Invoke-RestMethod http://localhost:8000/api/health; docker compose down`

Expected: Health JSON includes database, chat_model, and embedding_model component states.

- [ ] **Step 5: Commit the completed Stage 1 implementation**

```bash
git add .env.example README.md docker-compose.yml apps/api apps/web infra
git commit -m "feat: add stage one infrastructure"
```
