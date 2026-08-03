# DeepTutor 集成设计

## 1. Architecture

```text
Browser
  │ same-origin HTTP / WebSocket
  ▼
Nginx :80  ───────────────► FastAPI :8000 (127.0.0.1)
                              │
                              ├─ HTTP/WS adapter
                              ▼
                         DeepTutor :8001 (127.0.0.1)
                              │
                              ├─ shared LLM API
                              └─ shared Embedding API

PostgreSQL :5432 (separate Compose infrastructure container)
DeepTutor files: /app/runtime/deeptutor-data (named volume)
```

The `app` image contains the compiled React assets, Nginx, the existing API environment, and an isolated DeepTutor environment. The browser only knows the public application origin. Nginx proxies `/api/*` to FastAPI and enables connection upgrades for `/api/deeptutor/chat`.

## 2. Version and filesystem layout

- Base runtime: Python 3.13 slim. The current API dependencies run in `/opt/campus-venv`.
- DeepTutor: `deeptutor==1.5.8` installed only in `/opt/deeptutor-venv`.
- API source: `/app/app`; compiled frontend: `/usr/share/nginx/html`.
- DeepTutor home: `/app/runtime/deeptutor-data`, created by the entrypoint and mounted as `deeptutor_data:/app/runtime/deeptutor-data`.
- No host port maps to `8000` or `8001`; only `8080:80` is public for the app.

## 3. Container startup

`scripts/container-entrypoint.sh` is the single process coordinator. It:

1. Maps current `CHAT_*`/`EMBEDDING_*` variables to DeepTutor's environment contract and creates the writable data directory.
2. Starts `/opt/deeptutor-venv/bin/deeptutor serve --host 127.0.0.1 --port 8001`.
3. Polls `/api/v1/book/health` with a short request timeout and bounded attempts. It exits with a clear error if DeepTutor dies or never becomes ready.
4. Runs `alembic upgrade head`, starts Uvicorn on `127.0.0.1:8000`, and starts Nginx in the foreground.
5. Tracks all critical child PIDs. `SIGTERM`/`SIGINT` terminates them, waits for cleanup, and returns a failure code if any critical process exits unexpectedly.

Logs remain attached to the container's stdout/stderr: DeepTutor and Uvicorn inherit the entrypoint streams, and Nginx runs with `daemon off`.

## 4. Configuration mapping

| DeepTutor variable | Source / precedence | Notes |
|---|---|---|
| `LLM_BINDING` | explicit `LLM_BINDING`, otherwise `openai` | OpenAI-compatible providers use `openai` unless the installed DeepTutor version requires another binding. |
| `LLM_MODEL` | explicit `LLM_MODEL`, otherwise `CHAT_MODEL` | No model is hard-coded. |
| `LLM_API_KEY` | explicit `LLM_API_KEY`, otherwise `CHAT_API_KEY` | Never stored in image layers. |
| `LLM_HOST` | explicit `LLM_HOST`, otherwise `CHAT_BASE_URL` | Preserves the current OpenAI-compatible base URL. |
| `LLM_API_VERSION` | explicit value | Optional. |
| `EMBEDDING_BINDING` | explicit value, otherwise `openai` | Separate from the chat binding. |
| `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` | existing variables, with optional `DEEPTUTOR_EMBEDDING_MODEL` and chat-key fallback | Existing names match DeepTutor; a separate embedding key/model remains preferred when configured. |
| `EMBEDDING_HOST` | explicit `DEEPTUTOR_EMBEDDING_HOST`, otherwise existing `EMBEDDING_HOST`, otherwise derived `EMBEDDING_BASE_URL` + `/embeddings` | An explicit full endpoint wins; the suffix is not duplicated. |
| `EMBEDDING_DIMENSION` | explicit value, otherwise `DEEPTUTOR_EMBEDDING_DIMENSION`, otherwise `EMBEDDING_DIMENSIONS` | Must match the selected embedding model. |

The existing API keeps its own `CHAT_*`, `EMBEDDING_BASE_URL`, and plural `EMBEDDING_DIMENSIONS` settings. The mapping is a runtime concern only, so it does not alter existing model adapter behavior.

## 5. Backend boundary

`app.integrations.deeptutor.client.DeepTutorClient` owns all downstream URL construction, timeouts, response decoding, and WebSocket connection setup. Its public provider methods are:

- `health_check()`
- `list_books()`, `get_book(book_id)`, `get_spine(book_id)`, `get_page(book_id, page_id)`
- `create_or_compile_book(payload)`
- `list_knowledge_bases()`
- `chat_socket()` / `chat(...)`

`app.api.deeptutor` exposes stable app-facing routes:

- `GET /api/deeptutor/health`
- `GET /api/deeptutor/books`
- `GET /api/deeptutor/books/{book_id}`
- `GET /api/deeptutor/books/{book_id}/spine`
- `GET /api/deeptutor/books/{book_id}/pages/{page_id}`
- `POST /api/deeptutor/books`
- `GET /api/deeptutor/knowledge-bases`
- `WS /api/deeptutor/chat`

HTTP routes return the downstream JSON shape inside the existing API error envelope only when an error occurs. The WebSocket route forwards text/JSON messages without exposing the upstream host; connection and upstream errors close with an explanatory app-side WebSocket code/reason.

## 6. Health behavior

The existing `/api/health` remains a liveness/readiness-style endpoint. When `DEEPTUTOR_ENABLED=true`, it probes the adapter with a short timeout and adds a `deep_tutor` component. DeepTutor being unavailable makes the aggregate status `degraded` but does not stop FastAPI. The Docker healthcheck requires both API and DeepTutor while the app container is expected to be fully ready.

## 7. Frontend flow

`DeepTutorBookPanel` owns only its own list/detail/page/chat/create state. It uses functions added to the existing `src/api.ts`. The page chat uses a native WebSocket URL derived from `window.location`, pointing to `/api/deeptutor/chat`; it sends a session/page context payload and renders streamed text/events. No existing `useWorkspaceChat` state is duplicated.

The workspace navigation adds an `交互教材` section. A selected book loads its spine; a selected page loads page content; creating a book accepts a topic and optional knowledge-base selection; the question box sends the current book/page context.

## 8. Failure and rollback

- Missing model configuration: DeepTutor may start but book/chat operations return a clear unavailable/configuration error; the main app remains usable.
- DeepTutor startup failure: the container exits, Compose reports the app unhealthy, and no misleading partially-started app is left running.
- Runtime DeepTutor failure: API health becomes degraded and adapter routes return 502/503 through `AppError`.
- Rollback: switch back to `master` and use the prior `api` + `web` Compose services; the integration branch does not rewrite existing data or migrations.
