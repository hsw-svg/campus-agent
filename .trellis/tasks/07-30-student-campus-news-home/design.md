# 学生首页校园资讯技术设计

## Architecture

The feature remains one cross-layer deliverable because the fetch, cache, API degradation state, and UI presentation share one contract.

```text
Environment source config
        |
        v
RSS/Atom or HTML adapters -> URL/domain validation -> normalization
        |                                             |
        +---------------------> PostgreSQL cache <----+
                                      |
                              GET /api/campus-news
                                      |
                                apps/web/src/api.ts
                                      |
                          Student campus-center view
```

- `app.integrations.campus_news` owns HTTP access, redirect validation, and source-format parsing.
- `app.services.campus_news` owns source refresh orchestration, sample/live mode, freshness, fallback, and response assembly.
- `app.campus_news` owns SQLAlchemy models and repository operations.
- `app.api.campus_news` exposes the read-only API contract.
- The cache is global deployment data, not workspace-owned data. The endpoint may remain public because it returns only already-public official information and contains no student state.

## Runtime Configuration

Add settings without hard-coded school identity:

- `CAMPUS_NEWS_SOURCES_JSON`: blank selects sample mode. A nonblank JSON array defines source id, category, source label, format (`rss` or `html`), URL, allowed domains, and optional HTML selectors/date format.
- `CAMPUS_NEWS_REFRESH_SECONDS`: default `1800`.
- `CAMPUS_NEWS_MAX_STALE_SECONDS`: default `604800`.
- `CAMPUS_NEWS_REQUEST_TIMEOUT_SECONDS`: bounded per refresh.

HTML sources define selectors for the repeated item, title, date, link, optional summary, and optional activity end date. RSS/Atom uses standard feed fields. Invalid nonblank configuration is a degraded configuration error; it must not silently switch to samples. Blank configuration alone enables the neutral sample set.

The same variables are documented in `.env.example` and passed through `docker-compose.yml`. Add `beautifulsoup4` to the API project and Docker image for configured CSS selectors; RSS/Atom parsing uses the standard XML library.

## Persistence

Add Alembic revision `0012` and register models in both `app.main` and `alembic/env.py`.

### `campus_news_source_state`

- `source_id` string primary key
- `last_attempt_at`, `last_success_at`, `refresh_started_at` nullable timezone timestamps
- `last_error` nullable bounded text

### `campus_news_item`

- UUID primary key and indexed `source_id`
- category enum value stored as a bounded string: `news | activity | notice`
- title, optional summary, source label, official URL
- publication timestamp, optional activity end timestamp, fetched timestamp
- deterministic fingerprint unique within a source for deduplication

A successful source refresh replaces that source's cached item set in one transaction. A failed refresh updates source state but preserves the last successful items. Removed source ids are excluded from API results even if old rows remain.

## Refresh And Fallback

1. Blank source configuration returns nine generated neutral sample entries, three per category. Samples have `url = null`, remain non-clickable, and are never persisted or mixed with live data.
2. Fresh live cache returns immediately.
3. Cache older than the refresh interval returns immediately and schedules a bounded background refresh. A short refresh lease in source state prevents duplicate refresh work.
4. A cold live cache performs one bounded refresh before responding.
5. Partial source failure returns successful/current cached categories and marks the response degraded.
6. Failed refresh with cache no older than seven days returns that cache and marks it degraded.
7. Cache older than seven days is omitted. If nothing usable remains, return an empty degraded response rather than samples.

No website failure becomes an unhandled API error. Unexpected internal database errors still use the existing `AppError` envelope.

## HTTP And Parsing Security

- Accept only `http` and `https` source and item URLs.
- Validate hostnames against the configured official-domain allowlist using exact-domain or subdomain matching.
- Disable automatic redirects. Validate every redirect target before following it, with a small hop limit.
- Resolve relative item links against the source URL, normalize fragments away, and reject credentials or disallowed hosts.
- Bound response size, request duration, redirect count, parsed item count, title length, and summary length.
- Parse markup structurally. Do not execute scripts or copy detail-page HTML.
- Malformed items are skipped independently; a structurally unusable source refresh fails without deleting its previous cache.

## API Contract

`GET /api/campus-news` returns:

```json
{
  "mode": "sample",
  "status": "fresh",
  "refreshing": false,
  "last_success_at": null,
  "items": [
    {
      "id": "sample-news-1",
      "category": "news",
      "title": "校园教学成果交流活动顺利举行",
      "published_at": "2026-07-30T00:00:00+08:00",
      "event_end_at": null,
      "source": "校园新闻网",
      "summary": "...",
      "url": null
    }
  ]
}
```

- `mode`: `sample | live`.
- `status`: `fresh | stale | degraded`.
- `refreshing` tells the UI whether stale-while-refresh work was scheduled.
- Items are newest first, with at most three returned per category for this endpoint.
- Live items always have an allowed official URL. Sample items always have a null URL.
- Timestamps are timezone-aware ISO 8601 strings.

The Python response model is authoritative; matching TypeScript interfaces and `listCampusNews()` live in `apps/web/src/api.ts`.

## Frontend

Extract a focused `CampusNewsPanel` rather than expanding `StudentWorkspace` with parsing or fetching logic.

- `StudentWorkspace` owns a local `learning | campus` section state. The left navigation changes this state without modifying conversation state.
- Mount and fetch `CampusNewsPanel` only while the campus section is active; an API failure becomes a local panel empty/degraded state and never affects chat.
- The learning section owns the welcome/chat messages, composer, responsive resource picker, and desktop resource sidebar. The campus section renders none of those chat surfaces.
- Desktop (`sm` and above) shows three stable columns with up to three compact list entries per category.
- Mobile shows a three-option segmented control and up to three entries for the active category.
- Live entries use semantic external anchors with `target="_blank"`, `rel="noreferrer"`, an external-link icon, and an accessible label.
- Sample entries use non-interactive list markup and do not render an external-link affordance.
- Keep the existing learning-center welcome treatment and shortcuts independent from the campus-center content.
- Degraded live data receives a restrained freshness message; sample mode gets no visible demo label as requested.

## Compatibility And Rollback

- Existing workspaces, conversations, agents, and chat routes are unchanged; changing the selected section does not clear or recreate a conversation.
- Blank configuration makes local development deterministic without network access.
- The migration only creates new tables and can be downgraded without touching existing business data.
- Rollback consists of removing the router/component and downgrading revision `0012`; cached campus items are disposable.

## Future Detail And RAG Phase

This phase preserves stable source ids, canonical official URLs, and normalized metadata so a later task can add detail fetch records, cleaned document versions, chunks, embeddings, and citation-aware RAG. It intentionally does not fetch detail bodies, attachments, images, or create vectors now.
