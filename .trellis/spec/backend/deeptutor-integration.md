# DeepTutor Integration

## Scenario: Same-origin interactive books and page Q&A

### 1. Scope / Trigger

Use this contract when the application reads DeepTutor books, knowledge bases, pages, or chat streams. The integration is intentionally an HTTP/WebSocket boundary: the existing FastAPI service owns the browser-facing API and calls the local DeepTutor Server; application code must not import DeepTutor internals.

### 2. Signatures

- `GET /api/deeptutor/health -> { status, service, details? }`
- `GET /api/deeptutor/books -> upstream book list`
- `GET /api/deeptutor/books/{book_id} -> upstream book detail`
- `GET /api/deeptutor/books/{book_id}/spine -> upstream spine`
- `GET /api/deeptutor/books/{book_id}/pages/{page_id} -> upstream page`
- `POST /api/deeptutor/books?compile_page=false` accepts a JSON object and calls the create or compile-page upstream route.
- `GET /api/deeptutor/knowledge-bases -> upstream knowledge-base list`
- Internal textbook sync uses multipart `POST /api/v1/knowledge/create` and `POST /api/v1/knowledge/{kb_name}/upload` through `DeepTutorClient`.
- `WS /api/deeptutor/chat` proxies browser messages to DeepTutor's unified `/api/v1/ws` endpoint.

The adapter lives in `app.integrations.deeptutor.client.DeepTutorClient`. Browser-facing consumers use `app.api.deeptutor`; course Attachment upload is the only other allowed consumer and stores only stable KB/task state.

### 3. Contracts

- DeepTutor is pinned to `1.5.8`, runs in `/opt/deeptutor-venv`, listens on `127.0.0.1:8001`, and stores runtime data under `/app/runtime/deeptutor-data`.
- The Compose `app` service contains static React assets, Nginx, FastAPI, and DeepTutor. Only host port `8080` is published; Nginx proxies `/api/*` to FastAPI and upgrades `/api/deeptutor/chat`.
- `DEEPTUTOR_ENABLED` defaults to `false` for local API tests and is set to `true` in Compose. When enabled, `/api/health` adds `components.deep_tutor` and reports `degraded` if the local server is unavailable.
- Startup maps `CHAT_BASE_URL`, `CHAT_API_KEY`, and `CHAT_MODEL` to `LLM_HOST`, `LLM_API_KEY`, and `LLM_MODEL`. After DeepTutor becomes ready and before FastAPI starts, `app.integrations.deeptutor.catalog_sync` uses DeepTutor's localhost settings HTTP API to upsert and activate managed LLM/embedding profiles in its persistent model catalog. This synchronization is required because DeepTutor 1.5.8 resolves runtime providers from `model_catalog.json`, not directly from the legacy environment variables.
- Existing `EMBEDDING_MODEL` and `EMBEDDING_API_KEY` are reused, with an optional `DEEPTUTOR_EMBEDDING_MODEL` override and chat-key fallback; `EMBEDDING_HOST` must be a full embeddings endpoint and can be set with `DEEPTUTOR_EMBEDDING_HOST`.
- `EMBEDDING_DIMENSION` can be set explicitly with `DEEPTUTOR_EMBEDDING_DIMENSION`; it must match the selected embedding model. Changing it requires rebuilding the DeepTutor knowledge base.
- The React API client keeps payload normalization in `src/api.ts`; `DeepTutorBookPanel` owns only local book, page, and question UI state and does not duplicate `useWorkspaceChat` state.
- The upstream book endpoints use nested envelopes: spine responses are `{ spine: { chapters: [...] } }`, page responses are `{ page: {...} }`, and generated block text is commonly under `block.payload`. `src/api.ts` must unwrap these envelopes and expand chapter `page_ids` before the reader consumes them.
- Page Q&A uses a unified `start_turn` payload with `capability="chat"` and `book_references: [{ book_id, page_ids: [page_id] }]`. The legacy `/api/v1/chat` endpoint ignores `book_id` and `page_id`; `page-chat-session` only persists navigation metadata and does not inject page text into a prompt.
- Unified WebSocket `thinking`, status, tool, and result events are not answer deltas. The browser appends only eligible `content` events and stores the server-issued session ID from `session` events; this prevents reasoning traces such as `<think>` from appearing in the student-facing answer and preserves multi-turn history.
- Creating a usable book is a three-stage upstream workflow: create the proposal, confirm the proposal to generate a spine, then confirm the spine with `auto_compile=true` to create page shells and enqueue compilation. The browser-facing `POST /api/deeptutor/books` owns this orchestration; the React component must not open a proposal-only draft as though its spine already exists.
- `confirm-proposal` returns a pre-compilation spine whose chapters may not yet contain `page_ids`. After `confirm-spine`, `DeepTutorClient.create_or_compile_book` must re-fetch `GET /api/v1/book/books/{book_id}/spine` and return that latest spine to course-binding consumers.
- Compose allows up to 300 seconds for each local DeepTutor HTTP stage and Nginx allows 900 seconds for the complete browser request. Spine generation can exceed two minutes even with a healthy provider, so the shorter general-purpose API timeout must not be reused for book creation in the demo container.
- Local container development layers `docker-compose.dev.yml` over the production Compose file. It bind-mounts `apps/api/app` and the editable `apps/web` source paths with repository-relative paths, runs Uvicorn reload and Vite HMR inside the same `app` container, and swaps in `nginx.dev.conf`; Nginx still exposes only port `8080`, and DeepTutor remains private on `127.0.0.1:8001`.
- Student-side reading progress, notes, and saved questions are demo-only browser state under `campus-agent:deeptutor-study:<workspace-token-suffix>`; they do not replace DeepTutor's server-side book data or introduce a second application chat state.
- Course textbook sync receives bytes only after filename/size/course ownership checks and local parsing. DeepTutor degradation must not remove the local course material.

### Container development convention

The production and development Compose contracts are deliberately separate. Production uses `docker-compose.yml` with the Dockerfile `production` target and serves the built React assets from Nginx. Local container development overlays `docker-compose.dev.yml` and uses the `development` target:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

The development overlay must keep these repository-relative, read-only source mounts:

| Host path | Container path | Purpose |
|---|---|---|
| `./apps/api/app` | `/app/app` | Uvicorn reloadable FastAPI code |
| `./apps/api/alembic` | `/app/alembic` | migration source |
| `./apps/api/alembic.ini` | `/app/alembic.ini` | migration configuration |
| `./apps/web/src` | `/web/src` | Vite HMR React source |
| `./apps/web/index.html` | `/web/index.html` | Vite entry document |
| `./apps/web/vite.config.ts` | `/web/vite.config.ts` | Vite proxy/HMR configuration |
| `./infra/docker/nginx.dev.conf` | `/etc/nginx/conf.d/default.conf` | development reverse proxy |

With `CAMPUS_DEV_MODE=true`, the entrypoint starts DeepTutor on `127.0.0.1:8001`, FastAPI with `--reload --reload-dir /app/app`, Vite on `127.0.0.1:3000`, and Nginx on port `80` in that order. Host port `8080` remains the only published application port. Code-only edits under the mounted paths must not require an image rebuild; package manifests, dependencies, Dockerfiles, and runtime changes do require `--build`. Host `node_modules` must never be mounted into the Linux container.

### 4. Validation & Error Matrix

| Condition | Result |
|---|---|
| DeepTutor disabled or not configured | HTTP routes return `503 deeptutor_unavailable`; health reports `unavailable` without stopping FastAPI. |
| DeepTutor connection/timeout failure | Adapter maps to `503 deeptutor_unavailable`; WebSocket closes with code `1011`. |
| DeepTutor non-success HTTP response | Adapter maps to `502 deeptutor_upstream_error` with the upstream status and path in details. |
| Invalid upstream JSON | Adapter maps to `502 deeptutor_invalid_response`. |
| Final post-confirmation spine has no usable chapter page IDs | Course textbook endpoint returns `502 deeptutor_invalid_response` and does not bind local course rows. |
| DeepTutor startup readiness timeout | Container entrypoint exits non-zero before starting FastAPI or Nginx. |
| Critical child process exits after startup | Entrypoint terminates remaining children and exits non-zero. |
| Code-only edit under a development mount | Vite HMR or Uvicorn reload applies the change without rebuilding the image. |
| Dependency, Dockerfile, or package manifest edit | Rebuild the `development` target before restarting Compose. |
| Development overlay omitted | The base Compose file runs production static assets; source edits are not expected to hot reload. |

### 5. Good / Base / Bad Cases

- Good: the browser requests `/api/deeptutor/books` through port 8080, FastAPI calls `http://127.0.0.1:8001/api/v1/book/books`, and no client-visible URL contains port 8001.
- Good: local development starts `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`; source edits are observed through the mounted paths and the container remains healthy.
- Good: changing the embedding endpoint or dimension is done through environment variables and the knowledge base is rebuilt before the demo.
- Good: a page reader consumes normalized `DeepTutorPage.blocks` and can render a `payload.markdown` block without knowing the upstream envelope.
- Good: course textbook creation re-fetches the post-confirmation spine and persists page IDs that load through the same-origin page endpoint.
- Base: DeepTutor is unavailable while the existing workspace remains usable; `/api/health` is readable and marks the integration as degraded.
- Bad: adding a browser fetch to `http://localhost:8001`, publishing `8001:8001`, or importing DeepTutor Python modules into `apps/api`.
- Bad: mounting the host Windows `apps/web/node_modules` into the Linux container or changing the production Compose target to `development`.
- Bad: reading `response.page`, `response.spine.chapters`, or `block.payload` directly in multiple React components; that duplicates the upstream contract and breaks when the adapter shape changes.
- Bad: copying `.env` into a Docker build layer or placing API keys in a Dockerfile/source file.

### 6. Tests Required

- Adapter tests assert exact upstream book/knowledge paths and disabled integration errors.
- Book workflow tests assert the fourth request is the final spine GET and its page IDs replace the pre-compilation spine.
- Health tests assert the optional `deep_tutor` component does not alter the legacy response when disabled and marks a healthy probe when enabled.
- Compose tests assert the single `app` service, DeepTutor data volume, and absence of an `8001` host publication.
- Frontend checks run `npm.cmd run lint` and `npm.cmd run build`; the build must include `DeepTutorBookPanel` and same-origin WebSocket URL construction.
- Development checks run `docker compose -f docker-compose.yml -f docker-compose.dev.yml config`, assert the repository-relative mount targets, and smoke-test that Vite serves `/@vite/client` while Uvicorn runs with `--reload`.
- Deployment checks run `docker compose config`; when Docker Hub is reachable, build the app image and smoke-test `/api/health`, `/api/deeptutor/health`, the WebSocket proxy, and the container health status.

### 7. Wrong vs Correct

#### Wrong

```tsx
new WebSocket('ws://localhost:8001/api/v1/ws')
```

This bypasses the existing backend, exposes a private service, and makes deployment depend on a browser-reachable DeepTutor port.

#### Wrong: using production Compose for hot reload

```powershell
docker compose up -d
```

This starts the production static React target and does not mount editable source paths.

#### Correct: use the development overlay

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

The overlay selects the development target, mounts repository-relative source paths, and keeps the same-origin Nginx → FastAPI → DeepTutor boundary.

#### Correct

```tsx
new WebSocket(getDeepTutorChatWebSocketUrl())
```

#### Wrong: bind the proposal spine

```python
return {"spine": proposal_result["spine"]}
```

#### Correct: bind the post-confirmation spine

```python
await client.confirm_spine(book_id, auto_compile=True)
latest_spine = await client.get_spine(book_id)
return {"spine": latest_spine["spine"]}
```

The helper builds a same-origin `/api/deeptutor/chat` URL; Nginx and FastAPI perform the private hop to DeepTutor.
