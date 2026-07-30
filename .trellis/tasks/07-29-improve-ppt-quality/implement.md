# 实施计划

## Ordered Checklist

1. [ ] 收敛 PRD/design/implementation manifests，明确 native staged pipeline、权威 PPTX、失败策略和 PPTAgent deferred。
2. [ ] 为 `NanobotRunner` 增加可测试的 outline/batch/reflection 调用边界，并实现 8-12 页大纲、稳定 ID、两页批次、有界重试/拆分和 deterministic merge。
3. [ ] 将 `CourseIterationExecutorV2` 的 PPT 路径切换到 staged orchestrator，保留三种策略、previous deck context、citations/sources 和旧 `execute` 兼容。
4. [ ] 扩展 `SlideDeckJsonSkill` 的 stable ID 处理，并修正 `SlideDeckPptxSkill` 为 semantic slide 与 PPTX page 一一对应。
5. [ ] 实现配置化 LibreOffice -> PDF -> PyMuPDF PNG renderer，包含隔离 profile、timeout、清理和 unavailable errors。
6. [ ] 扩展 Artifact model/schema/repository 和 Alembic migration，保存权威二进制与 preview metadata；沿用现有 ObjectStorage。
7. [ ] 在 conversation finalization 中一次生成 PPTX、存储、从已存储 bytes 渲染并保存 previews；全部就绪后才写 artifact/SSE，失败清理对象。
8. [ ] 增加 owned preview manifest/page API；export 对新 artifact 流式返回存储 PPTX，对 legacy 保留 re-render。
9. [ ] 同步 API/SSE/frontend types 与 `SlideDeckPreview`，新 artifact 只展示 PPTX 派生 PNG，legacy 保持 JSON/CSS。
10. [ ] 增加 staged runtime、skill/page count、renderer、migration、API ownership/export/preview 和前端兼容测试。
11. [ ] 运行 focused tests、完整 non-integration pytest、compileall、uv lock check、前端 lint/build 和 diff check。
12. [ ] 仅在自动化检查通过后执行一次真实 DeepSeek 验证；文件仅放 `$CLAUDE_JOB_DIR/tmp`，检查 IDs/order、PPTX/preview 页数和页面文本对应。

## Validation Commands

```bash
cd apps/api && ../../.venv/Scripts/python.exe -m pytest tests/agents tests/skills tests/api/test_artifacts_export.py tests/api/test_artifact_previews.py
cd apps/api && ../../.venv/Scripts/python.exe -m pytest -m "not integration"
cd apps/api && ../../.venv/Scripts/python.exe -m compileall app
cd apps/api && uv lock --check
cd apps/web && npm.cmd run lint
cd apps/web && npm.cmd run build
git diff --check
```

Migration validation additionally runs `alembic upgrade head` when the configured PostgreSQL integration environment is available. Renderer tests mock LibreOffice and PyMuPDF; a local LibreOffice installation is not a unit-test prerequisite.

## Review Gates

- Stage contracts reject counts/IDs outside the expected set and no test observes a monolithic full-deck call.
- Retry counts are asserted and cannot grow without bound.
- Semantic slide count equals PPTX page count equals preview manifest count.
- New authoritative artifacts never use JSON/CSS fallback; legacy artifacts retain it.
- Ownership is checked before exposing manifest, PNG bytes, or PPTX bytes.
- Failure tests prove no artifact event is emitted and staged object keys are deleted.

## Risky Files and Rollback Points

- `apps/api/app/agents/nanobot/` and `course_iteration_v2.py`: retain public runner compatibility and isolate staged orchestration.
- `apps/api/app/skills/slide_deck_json.py` / `slide_deck_pptx.py`: legacy normalization/export tests are the rollback gate.
- Artifact model/migration/repository: fields remain nullable and additive.
- Conversation finalization: preserve old text/JSON artifact behavior and emit SSE only after durable success.
- Preview/export API and frontend: branch explicitly on authoritative metadata, never infer from artifact kind alone.

## Deferred Work

Direct PPTAgent/DeepPresenter integration remains research only. Durable stage checkpoint/resume, partial-deck delivery, richer template engines, and external conversion workers require separate approved tasks.
