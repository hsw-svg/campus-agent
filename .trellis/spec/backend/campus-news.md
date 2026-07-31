# Campus News Contract

## Scenario: Public official campus information on the student home

### 1. Scope / Trigger

- Use this contract when changing campus-news source configuration, parsing, cache persistence, `GET /api/campus-news`, or the student empty-state panel.
- The feature aggregates public official metadata only. It does not fetch detail bodies, attachments, images, authenticated notices, or workspace-owned records.

### 2. Signatures

- API: `GET /api/campus-news` (public, read-only).
- Source entry: `id`, `category`, `source`, `format`, `url`, `allowed_domains`; HTML sources also require item/title/date/link selectors.
- DB tables: `campus_news_source_state(source_id, last_attempt_at, last_success_at, refresh_started_at, last_error)` and `campus_news_item(..., source_id, category, url, published_at, fingerprint)`.
- Integration: `fetch_source(source, timeout_seconds) -> tuple[NormalizedCampusNewsItem, ...]`.

### 3. Contracts

- `CAMPUS_NEWS_SOURCES_JSON` blank means sample mode. A nonblank invalid value means degraded live mode and must never fall back to samples.
- `CAMPUS_NEWS_REFRESH_SECONDS` defaults to `1800`; `CAMPUS_NEWS_MAX_STALE_SECONDS` defaults to `604800`; `CAMPUS_NEWS_REQUEST_TIMEOUT_SECONDS` defaults to `6`.
- Response fields are `mode`, `status`, `refreshing`, `last_success_at`, and `items`. Items contain `id`, `category`, `title`, `published_at`, `event_end_at`, `source`, `summary`, and `url`.
- Sample items always have `url = null`. Live items always have a validated official HTTP(S) URL. Return at most three newest usable items per category.
- The frontend fetches only while the student `campus` section is mounted; desktop renders three columns and mobile renders one selected category. The `learning` section exclusively owns chat messages, composer, and resource surfaces.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Blank source JSON | Nine neutral, non-clickable sample items; `mode=sample`, `status=fresh` |
| Invalid nonblank config | Empty `mode=live`, `status=degraded`; never mix samples |
| Disallowed scheme, credentials, host, or redirect | Reject before following or caching the URL |
| Oversized response, timeout, HTTP error, unusable parse | Preserve the last successful source cache and record a bounded error |
| Cache older than max stale | Omit it from API results |
| SQLAlchemy cache failure | Raise stable `AppError(code="campus_news_cache_unavailable", status=503)` |

### 5. Good/Base/Bad Cases

- Good: an official RSS redirect remains inside an allowed domain, parses usable items, and atomically replaces only that source's cache.
- Base: no source is configured, so local and demo deployments render neutral metadata without external links or school identity.
- Bad: an HTML item links to `official.edu.cn.evil.test`; skip that item and never request or expose the URL.

### 6. Tests Required

- Unit: JSON source validation, exact/subdomain allowlist matching, RSS and selector HTML parsing, redirect validation before follow, and response-size bounds.
- Service: cold refresh, successful replacement, failed refresh preserving cache, partial failure, expired-cache omission, activity end-date filtering, and three-per-category limit.
- API: blank sample response, invalid-config degradation, and stable database error envelope.
- Frontend: `npm.cmd run lint` and `npm.cmd run build`; browser QA at desktop/mobile sizes must verify category presentation, zero sample external links, mobile switching, left-menu section switching, conversation preservation, and mutual exclusion of campus content versus chat/resource surfaces.
- Migration: generate offline SQL from base and run `alembic upgrade head` against PostgreSQL. If the database revision is absent from the repository, stop and restore the original migration; never stamp or invent history to make this feature pass.

### 7. Wrong vs Correct

#### Wrong

```python
response = await client.get(source.url, follow_redirects=True)
return sample_response() if response.is_error else parse(response)
```

This follows unvalidated redirects and can mix fictional samples into a configured live deployment.

#### Correct

```python
response = await client.get(current_url, follow_redirects=False)
current_url = validate_official_url(redirect_target, source.allowed_domains)
# Preserve live cache and return degraded live data on upstream failure.
```
