# 学生首页校园资讯实施计划

## Ordered Checklist

1. Define campus-news settings and source-config validation; document/pass the environment variables through Compose.
2. Add the HTML parser dependency consistently to `pyproject.toml` and the API Docker image.
3. Add campus-news models, repository operations, model registration, and Alembic revision `0012`.
4. Implement canonical URL/domain validation, bounded redirect handling, RSS/Atom parsing, and selector-driven HTML parsing as isolated integration code.
5. Implement the service refresh state machine: neutral samples, fresh cache, stale-while-refresh, cold bounded refresh, partial failure, seven-day cutoff, and refresh lease.
6. Add `GET /api/campus-news` response models and register the router in `create_app`.
7. Add backend unit/API tests for configuration, parsers, redirect/domain rejection, sample response, live response, cache fallback, partial failure, and over-age omission.
8. Add matching TypeScript contracts and `listCampusNews()` in `apps/web/src/api.ts`.
9. Build `CampusNewsPanel` with loading, sample, live, degraded, empty, desktop three-column, and mobile segmented states.
10. Add a `learning | campus` student-workspace section state, a left-menu “校园中心” item, and render the panel only in the campus section; keep chat, composer, and resource surfaces in the learning section.
11. Run migrations and the full directly related verification matrix, then inspect desktop/mobile screenshots and interactions.

## Likely Files

- `.env.example`
- `docker-compose.yml`
- `infra/docker/api.Dockerfile`
- `apps/api/pyproject.toml`
- `apps/api/app/core/config.py`
- `apps/api/app/main.py`
- `apps/api/app/api/campus_news.py`
- `apps/api/app/campus_news/{models,repositories}.py`
- `apps/api/app/integrations/campus_news/*.py`
- `apps/api/app/services/campus_news.py`
- `apps/api/alembic/env.py`
- `apps/api/alembic/versions/0012_*.py`
- `apps/api/tests/**/test_campus_news*.py`
- `apps/web/src/api.ts`
- `apps/web/src/components/CampusNewsPanel.tsx`
- `apps/web/src/components/StudentWorkspace.tsx`

Exact file splits may be reduced if a module would otherwise contain only trivial forwarding code.

## Validation

```powershell
cd apps/api
..\..\.venv\Scripts\python.exe -m pytest
..\..\.venv\Scripts\python.exe -m pytest -m integration tests/integration
..\..\.venv\Scripts\python.exe -m alembic upgrade head

cd ..\web
npm.cmd run lint
npm.cmd run build

cd ..\..
docker compose config
git diff --check -- .env.example docker-compose.yml infra apps/api apps/web
```

Browser verification at desktop and mobile sizes must cover:

- all three desktop categories and mobile category switching;
- non-clickable neutral samples;
- live official links opening safely;
- degraded/stale and empty states;
- learning/campus menu switching without clearing an existing conversation;
- no news in the learning section and no chat composer/resource sidebar in the campus section;
- no overlap with the header, chat composer, sidebar, or resource panel.

## Risk And Rollback Points

- Parser correctness: keep RSS and HTML fixtures local and test malformed/missing fields before connecting a real school.
- SSRF/open redirects: URL validation is a release blocker; do not weaken allowlist checks to make fixtures pass.
- Cache replacement: only delete/replace a source's items after a complete successful parse.
- Background refresh: verify request sessions are not reused after response and duplicate refreshes are leased.
- Migration: verify SQLite unit metadata and PostgreSQL/Alembic registration; downgrade only the new cache tables if rollback is required.
- UI density: inspect actual screenshots rather than relying only on TypeScript/build success.

## Start Gate

Implementation starts only after the user reviews `prd.md`, `design.md`, and this checklist and explicitly approves task activation.

## Execution Status (2026-07-30)

- [x] Backend source validation, RSS/HTML parsing, bounded redirect fetching, persistent cache, degradation service, API route, migration, and regression tests implemented.
- [x] Campus-center desktop/mobile panel and left-menu view separation implemented per the 2026-07-31 requirement change; Docker QA confirmed no composer/resource sidebar in campus view and preserved learning-view draft state across switching.
- [x] Full backend unit suite, frontend lint/build, Compose config, offline Alembic SQL, and diff whitespace checks passed.
- [ ] Standard `docker compose up` API startup remains blocked by the pre-existing database revision `0012_artifact_presentation`, whose migration file is absent from the repository. Do not stamp or synthesize that unrelated migration without an explicit recovery decision.
