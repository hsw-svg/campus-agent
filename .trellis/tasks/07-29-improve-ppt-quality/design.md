# 技术设计：原生分阶段 PPT 生成与权威预览

## Architecture Decision

PPTAgent 的评估结论只用于借鉴“轻量大纲 -> 小粒度页面生成 -> 局部校验/重试 -> 本地组装”的架构。当前版本不加载 PPTAgent runtime。现有 router、`CourseIterationExecutorV2`、`NanobotRunner`、provider、skills、artifact、SSE 和前端边界保持为系统主链路。

## End-to-End Data Flow

```text
PPT intent
  -> research/context assembly
  -> staged outline call (metadata + 8-12 plans)
  -> assign slide-001..N
  -> detail batches (2 slides, bounded concurrency <= 2)
  -> stage validation + targeted retry/single-slide split
  -> optional one-pass reflection defect list + defective-slide regeneration
  -> deterministic local merge
  -> SlideDeckJsonSkill normalization
  -> SlideDeckPptxSkill exactly once
  -> object storage: authoritative PPTX
  -> LibreOffice PDF conversion from stored bytes
  -> PyMuPDF PNG pages
  -> object storage: all previews
  -> one Artifact DB row + SSE artifact event
```

No normal artifact exists before the final persistence step. A failed object write, conversion, page-count check, or DB operation cleans objects written by this run.

## Staged Runtime Contracts

`NanobotRunner.execute()` remains backward compatible for existing callers. PPT execution uses explicit staged methods with model-call boundaries that can be mocked: `generate_slide_outline`, `generate_slide_batch`, and reflection-only `identify_slide_defects`.

The orchestrator owns retries, batch splitting, merge and final normalization. Provider responses expose text and optional `stop_reason`; correctness cannot depend on unavailable raw `finish_reason`.

Outline plans are lightweight and do not contain full bullets/notes/media. Stable IDs are assigned locally after validating an exact 8-12 plan count. Every detail response must contain exactly the expected IDs once. Batch size defaults to 2; execution may be sequential or use a semaphore of 2, with deterministic merge by outline order.

Recovery is finite: initial batch call; one correction call for parse/schema/ID failure; if still invalid or length-stopped, one-slide calls with bounded attempts per slide. Any remaining invalid slide fails the run and valid batches are not regenerated.

Reflection performs one compact defect-list call after merge, accepts only known IDs, and regenerates only those slides. `react` keeps tool/research-oriented prompting; `plan_and_solve` strengthens outline sequencing; neither changes the bounded pipeline.

## Semantic Deck Contract

`SlideDeckJsonSkill` is the final schema owner. It preserves supplied stable IDs, synthesizes deterministic IDs for legacy input, de-duplicates/normalizes while retaining order, and preserves title/topic, summary, notes, citations, media and sources. Previous deck context and source catalog are provided to outline/detail prompts and carried into final data.

`SlideDeckPptxSkill` receives only the normalized final deck and emits exactly one PPTX slide per semantic slide. It does not add a hidden or implicit cover. This creates a direct order mapping between `slides[n].id`, PPTX page `n + 1`, and preview manifest entry `n`.

## Authoritative Binary and Preview

For new presentations, artifact binary metadata is nullable but complete as a set: `object_key`, `mime_type`, `sha256`, `size_bytes`, `page_count`, `preview_status`, and an ordered `preview_manifest` containing slide ID, page number, PNG object key, MIME, hash and size.

The PPTX object is written first. The renderer is invoked with bytes read back from object storage, making the stored binary the exact conversion input. It creates a unique temp directory, writes `input.pptx`, uses an isolated LibreOffice profile, enforces timeout and nonzero-exit handling, locates the generated PDF, and rasterizes it with PyMuPDF. Temporary files are scoped to the call and always removed.

The configured converter path may be an absolute executable path or command name. Missing executable/package, timeout, conversion failure, absent PDF, and page-count mismatch have clear errors. Unit tests mock subprocess/PyMuPDF; deployment may install LibreOffice in Docker, but local unit tests do not require it.

## Persistence and Failure Policy

Artifact columns are added by a nullable, legacy-compatible Alembic revision. Existing JSON/text artifact behavior is unchanged. New authoritative artifact creation normalizes JSON and creates PPTX bytes once, stores PPTX, reads that object and renders previews, stores all PNG objects, validates count/order, then inserts one Artifact row. Only after that may the artifact SSE event be emitted.

On failure, every object key successfully written by this operation is deleted best-effort and no completed artifact row/event is produced. Database/object storage cannot share a transaction, so cleanup plus artifact-scoped immutable keys is the practical atomicity boundary.

## API and Frontend

- `GET /api/artifacts/{id}/export`: stream stored bytes when `object_key` exists; otherwise retain legacy re-render fallback.
- `GET /api/artifacts/{id}/previews`: return ordered manifest for an owned authoritative artifact.
- `GET /api/artifacts/{id}/previews/{page}`: resolve only a manifest-listed key and stream that PNG.

All routes call `get_owned_artifact`; object keys are never accepted from clients. Artifact response/SSE includes binary metadata and preview status/manifest projection. The frontend displays ordered page images for authoritative artifacts and preserves JSON for semantic metadata and iteration. It uses legacy JSON/CSS rendering only when no authoritative object exists.

## Compatibility, Rollout, and Rollback

Existing `NanobotRunner.execute` callers remain valid. Legacy artifacts have null binary columns and continue current export/preview behavior. New stable IDs are additive and deterministic for legacy input. Rollback can disable authoritative generation at the executor/service boundary and leave nullable columns in place. PPTAgent remains deferred research until a separate worker/runtime task is approved.
