# 改善 PPT 生成质量与预览一致性

## Goal

让 `course_iteration` 的 PPT 请求稳定生成可交付的 8-12 页教学课件，避免单次完整 JSON 响应被长度截断，并保证浏览器预览与下载的 PPTX 来自同一个最终文件。

## Confirmed Constraints

- 继续使用 campus-agent 现有路由识别 PPT 意图，并由 `CourseIterationExecutorV2` / `NanobotRunner` 执行。
- 采用原生分阶段生成；PPTAgent 仅作为架构研究参考，本期不直接集成其 runtime、CLI、容器或模板系统。
- 三种策略 `react`、`plan_and_solve`、`reflection` 保持平级语义，但都必须走分阶段链路。
- 成功产物包含语义 `slide_deck` JSON、恰好一次生成的最终 PPTX、以及从该存储 PPTX 派生的逐页 PNG 预览。
- 不允许以 JSON/CSS 近似预览替代新权威 PPTX 的实际渲染结果。
- 旧 artifact 继续支持文本/JSON 读取和按需重新导出，不要求迁移已有二进制。
- 保留先前课件上下文、引用、来源和稳定页序。

## Requirements

### R1. 分阶段生成

- 大纲阶段返回元数据和恰好 8-12 个轻量页面计划，不生成完整讲稿。
- 大纲通过校验后，本地按顺序分配 `slide-001`、`slide-002` 等稳定 ID。
- 页面详情默认每批 2 页，顺序执行或并发上限 2；每批只能返回预期 ID。
- 每批立即解析和校验；成功批次本地合并，最终统一通过 `SlideDeckJsonSkill`。
- 不得再发送一次完整 8-12 页详情的模型调用。

### R2. 有界恢复策略

- 批次解析失败、缺页/多页、ID 不匹配时，只针对该批重试一次。
- 若重试后仍失败，或响应 `stop_reason` 表示长度截断，将该批拆成单页调用；单页尝试次数有明确上限。
- 不进行无限重试，也不因单批失败重启整份课件。
- 最终仍缺页时任务失败，不持久化半成品正常 artifact。
- `reflection` 只做一次紧凑缺陷识别，并仅重生成明确有缺陷的页/批；其他模式不增加全量重生成。

### R3. 语义契约与渲染

- `SlideDeckJsonSkill` 接受并保留稳定 slide ID，同时兼容没有 ID 的旧数据。
- 最终 JSON 保留 previous deck context、notes、citations、media、sources 和页面顺序。
- `SlideDeckPptxSkill` 对每个语义 slide 只生成一页，不额外插入未表示的封面。
- PPTX 仅在最终语义 JSON 完成后生成一次，随后存储并作为视觉事实来源。

### R4. PPTX 派生预览

- 渲染器读取存储的 PPTX bytes，在请求本地临时目录内调用配置的 LibreOffice/`soffice` 转成 PDF，再用 PyMuPDF 逐页生成 PNG。
- LibreOffice 使用隔离 profile、超时、可靠清理；不可用时返回清晰错误，不使用 PowerPoint COM，也不宣称纯 Python 可栅格化 PPTX。
- converter 路径由 `Settings` 的 `PPTX_CONVERTER_PATH` 配置；单元测试不依赖本机安装。
- PNG 页与 semantic slides 通过稳定 ID 和顺序对应，页数必须一致。

### R5. 原子持久化与 API

- Artifact 可选保存 PPTX object key、MIME、SHA-256、字节数、页数，以及 preview manifest/status；新增字段 nullable，兼容旧记录。
- 数据库变化使用 Alembic migration；对象存储沿用现有 workspace ownership 和本地实现。
- 只有语义 JSON、PPTX 存储和全部预览存储完成后，才能创建完成 artifact 并发送 artifact SSE。
- 失败时清理本次已写入的对象，不留下“已完成”普通 artifact。
- 新 artifact 导出直接流式读取权威 PPTX；旧 artifact 保留从 JSON 重新渲染的 fallback。
- 新增已认证、经 `get_owned_artifact` 授权的预览 manifest/page API。

### R6. 前端

- API、SSE 和前端类型表达 authoritative presentation 与 preview 状态。
- `SlideDeckPreview` 对权威 artifact 展示实际 PPTX 派生 PNG；如果预览不可用，显示明确状态，不静默退回 JSON/CSS。
- 仅没有 authoritative presentation 的 legacy artifact 使用旧 JSON/CSS 预览。

## Acceptance Criteria

- [ ] Outline 契约强制 8-12 个计划，并在详情调用前分配稳定 ID。
- [ ] 详情调用默认两页一批、并发不超过 2，具备批次一次重试和有界单页拆分恢复。
- [ ] 三种策略保留现有选择语义；reflection 仅重生成缺陷页。
- [ ] 最终 JSON 通过 `SlideDeckJsonSkill`，且 IDs、顺序、上下文、引用和来源完整。
- [ ] PPTX 页数严格等于 semantic slides 数，且只生成一次。
- [ ] 存储 PPTX 的 hash、size、MIME、page count 与 preview manifest 可通过 API 获取。
- [ ] preview PNG 全部来自已存储的同一 PPTX，页数与 semantic slides 一致。
- [ ] 新 artifact 的 preview/download 不分叉；legacy artifact 仍可导出和旧式预览。
- [ ] 未完成全部核心产物时，不创建正常 artifact、不发送 artifact SSE，并清理 staged objects。
- [ ] 覆盖 staged orchestration、PPTX 页数、renderer、迁移、API ownership/export/preview 和前端契约的自动化检查通过。
- [ ] 自动化检查通过后至多执行一次真实 DeepSeek 验证；输出仅写入 `$CLAUDE_JOB_DIR/tmp`，结果如实报告。

## Out of Scope

- 直接集成 PPTAgent / DeepPresenter runtime、MCP、Playwright、Docker worker 或模板诱导。
- PowerPoint COM 渲染或任意 JSON/CSS 对权威 PPTX 的像素级近似。
- 持久化分阶段 checkpoint 或向用户交付部分课件。
- 修改非 PPT agent 的执行路径。
