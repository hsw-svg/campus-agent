# DeepTutor 集成

## Goal

在竞赛演示场景下，把 DeepTutor 的交互式书本、知识库查询和页面问答能力接入现有校园 AI 工作台。浏览器只访问现有应用入口，由现有 FastAPI 后端统一代理到同一容器内的 DeepTutor Server，避免暴露 DeepTutor 端口和引入第二套 API Key。

本任务优先保证可部署、可诊断和可现场演示，不扩展真实用户、权限、多租户或生产级并发模型。

## Confirmed Context

- 现有后端是 `apps/api` 下的 FastAPI 应用工厂 `app.main.create_app`，运行端口为 `8000`。
- 现有前端是 `apps/web` 下的 React 19 + Vite 应用，生产构建输出静态文件，Compose 当前通过 Nginx 暴露 `8080`。
- 现有 Compose 将数据库、API、Web 拆成三个服务；本任务将应用运行时收敛为一个包含 Nginx、FastAPI 和 DeepTutor 的 `app` 容器，数据库仍保留为基础设施容器。
- 现有模型变量使用 `CHAT_BASE_URL`、`CHAT_API_KEY`、`CHAT_MODEL` 以及 `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`、`EMBEDDING_DIMENSIONS`。
- DeepTutor 固定使用 `1.5.8`，在 `/opt/deeptutor-venv` 中独立安装，运行数据固定在 `/app/runtime/deeptutor-data`。

## Requirements

### R1. Runtime and isolation

- Pin the DeepTutor package version and use a Python 3.13-compatible image.
- Install DeepTutor into `/opt/deeptutor-venv`; do not merge its dependencies into the existing API environment.
- Run DeepTutor on `127.0.0.1:8001` only. The application container exposes only the existing web entry port (`80`, mapped to host `8080`) and database infrastructure ports.
- Set `DEEPTUTOR_HOME=/app/runtime/deeptutor-data` and persist that directory through a named Compose volume.

### R2. Shared model configuration

- Reuse the existing `CHAT_*` and `EMBEDDING_*` settings by mapping them to DeepTutor's `LLM_*` and `EMBEDDING_*` environment contract at container startup.
- Do not copy `.env` into the image or hard-code secrets.
- Allow explicit DeepTutor overrides for binding, model, host, API version, embedding endpoint, and dimension.
- Treat the embedding host as an embeddings endpoint: use an explicit override when supplied, otherwise derive `/embeddings` from the existing embedding base URL without duplicating the suffix.
- Document that changing the embedding model or dimension requires rebuilding the DeepTutor knowledge base.

### R3. Process orchestration and health

- Start DeepTutor first and poll its book health endpoint until it responds or a bounded startup deadline is reached.
- Run migrations and then start the existing FastAPI backend; serve the React build through the same container's Nginx.
- Forward termination signals, reap/stop child processes, stream service logs to stdout/stderr, and fail the container when a critical child exits.
- Add a Docker healthcheck for the existing backend and DeepTutor book health endpoint.
- Do not use a fixed sleep as the readiness test.

### R4. Backend adapter and API surface

- Add one isolated `InteractiveBookProvider`/DeepTutor HTTP client under `app.integrations`; business routes must not issue scattered raw requests.
- Support health, book listing/detail/spine/page retrieval, book creation/compilation, knowledge-base listing, and chat through HTTP/WebSocket.
- Add FastAPI routes under `/api/deeptutor` for the frontend. Proxy chat WebSocket traffic through FastAPI to DeepTutor; the browser must never connect to port `8001` directly.
- Normalize downstream errors into the project's stable `AppError` JSON shape and return a degraded health component when DeepTutor is unavailable.

### R5. Frontend demo flow

- Add an "交互教材" workspace entry that lists available DeepTutor books and knowledge bases.
- Allow the presenter to select a book/page, read page content, create a book from a topic, and ask questions in the selected page/book context.
- Keep DeepTutor state local to the feature component; do not create a second global chat/run state or modify the existing workspace-chat flow.
- Use the existing API client conventions and surface loading, empty, unavailable, and downstream error states.

### R6. Documentation and verification

- Update `.env.example`, Compose/Docker documentation, and the project README with startup, persistence, port, model mapping, pre-generation, and embedding rebuild notes.
- Add backend adapter/route tests using mocked HTTP/WebSocket boundaries and configuration mapping tests where practical.
- Run targeted backend tests, frontend lint/build, Docker Compose configuration validation, and a container/proxy smoke check when Docker is available.

## Acceptance Criteria

- [ ] A new `codex/deeptutor-integration` branch contains the implementation; the original branch is not modified during development.
- [ ] `docker compose config` describes one `app` container for React static files, FastAPI, and DeepTutor, plus the existing database infrastructure; no `8001` host port is published.
- [ ] The application image installs DeepTutor `1.5.8` in `/opt/deeptutor-venv`, uses Python 3.13, and does not copy `.env` or secrets.
- [ ] Container startup verifies `http://127.0.0.1:8001/api/v1/book/health` before starting the API and exits clearly on timeout or child failure.
- [ ] `GET /api/health` continues to work and reports a separate DeepTutor component when integration is enabled; an unavailable DeepTutor produces a degraded status rather than taking down the API process.
- [ ] `/api/deeptutor` HTTP routes and `/api/deeptutor/chat` WebSocket proxy work through the existing application origin, with no browser-facing DeepTutor URL.
- [ ] The React workspace can list books/knowledge bases, inspect a page, create a book, and submit a contextual page question with visible failure/loading states.
- [ ] Model mapping is explicit, configurable, secret-free in examples, and documents endpoint/dimension compatibility.
- [ ] Relevant tests and build checks pass, and unrelated pre-existing worktree changes are preserved.

## Out of Scope

- DeepTutor's own frontend or a second browser-facing UI process.
- Database-level synchronization between course records and DeepTutor books.
- New accounts, JWT, role permissions, multi-tenant book isolation, or production concurrency controls.
- Automatic bulk conversion of every existing course attachment into a DeepTutor knowledge base; the demo can prepare the primary books/knowledge bases before the event.
