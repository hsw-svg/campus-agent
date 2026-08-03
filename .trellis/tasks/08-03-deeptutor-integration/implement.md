# DeepTutor 集成实施清单

## Phase 1: planning gate

- [x] Inspect repository layout, backend/frontend entrypoints, dependency files, Compose, Dockerfiles, startup script, env names, API clients, and course contracts.
- [x] Inspect Git state and create `codex/deeptutor-integration` from `master` without touching unrelated work.
- [x] Verify the upstream DeepTutor version, CLI serve command, REST routes, WebSocket routes, and environment names.
- [x] Record requirements and design in `prd.md` and `design.md`.
- [x] Validate and start the Trellis task.

## Phase 2: runtime and configuration

- [x] Pin DeepTutor and add the isolated venv installation to a single production app Dockerfile.
- [x] Add the container entrypoint with environment mapping, readiness polling, migration/API/Nginx ordering, signal handling, and critical-process monitoring.
- [x] Replace the split production API/Web services in Compose with one app service and a persistent DeepTutor data volume.
- [x] Add same-origin Nginx HTTP/WebSocket proxy rules and Docker healthcheck.
- [x] Update `.env.example`, `.dockerignore`, and deployment documentation.

## Phase 3: backend adapter

- [x] Add typed DeepTutor client/protocol under `app.integrations.deeptutor`.
- [x] Add app-facing HTTP routes and a FastAPI WebSocket proxy under `app.api.deeptutor`.
- [x] Extend settings and health reporting without making DeepTutor absence crash the base API.
- [x] Add mocked adapter/route/configuration regressions.

## Phase 4: frontend demo flow

- [x] Add shared DeepTutor request/response types and client functions to `src/api.ts`.
- [x] Add a local-state `DeepTutorBookPanel` for books, knowledge bases, pages, book creation, and contextual WebSocket Q&A.
- [x] Add the navigation entry and render path in `StudentWorkspace`.
- [x] Verify loading, empty, unavailable, error, and streaming states without changing the existing workspace-chat hook.

## Phase 5: verification and handoff

- [x] Run targeted backend tests and all relevant API tests.
- [x] Run frontend lint and production build.
- [x] Run `docker compose config`; Docker image build was attempted but Docker Hub registry access was unavailable in the environment, so runtime smoke testing remains pending.
- [x] Run Trellis quality check and update the active spec with reusable DeepTutor integration conventions.
- [x] Review diff/status for unrelated changes.
- [ ] Present a single commit plan, obtain commit confirmation according to Trellis workflow, commit the integration branch, merge it into `master`, and leave the working tree clean except for explicitly pre-existing files.
