# 设计文档

## 架构总览

```
教师工作台 → SSE ─▶ agents/executors/course_iteration.py（新）
                       ├─ 聚合课程 artifact（learning_analysis / classroom_summary / grading）
                       ├─ integrations/search/bing.py.search(topic + query template)（并发两次）
                       ├─ integrations/llm.ChatProvider → JSON mode 输出 slide_deck.data
                       └─ AgentArtifact(type=slide_deck, content=markdown, data=json)
                          │
                          └─ artifact 落库；SSE 发送 artifact 事件
                                │
                前端 useWorkspaceChat 收到 → artifacts 状态更新 → TeacherWorkspace 渲染 SlideDeckPreview
                                                                        │
                                                                下载 PPTX → /api/artifacts/{id}/export?format=pptx
                                                                        │
                                                                skills/slide_deck_export.py → python-pptx → BytesIO
```

## 后端

### 1. AgentExecutor：`course_iteration.py`

- 新文件 `apps/api/app/agents/executors/course_iteration.py`。
- 触发条件（在 `execute` 里判断）：
  - 若最近一次消息内容包含「课件 | 幻灯 | slide | ppt | PPT | 演示文稿」→ 走 slide_deck 分支。
  - 否则走 `GenericChatExecutor`（保持现有课程迭代文字建议行为）。
- slide_deck 分支步骤：
  1. **收集课程上下文**：从 `request.context.selected_artifacts` + `request.context.course_context.course_id`（若存在）拿到本课程内最新的一份 `learning_analysis`、`classroom_summary`、`grading` 摘要。若没有则字段留空。
  2. **联网检索**：`BingSearchProvider.search(query, count=5)` 两次：
     - `"{topic} 最新应用 案例 2025"` → `industry_updates`
     - `"{topic} 岗位 技能 招聘 应届生"` → `job_skill_focus`
     若 provider 未配置，`search()` 返回 `SearchResult(results=[], available=False)`；写入 warning。
  3. **上一版 artifact 载入**：`ArtifactRepository.latest_by_conversation(conversation_id, type="slide_deck")` 取回，作为「先前版本」注入 prompt。
  4. **调用 LLM**：使用 `ChatProvider.stream_reply` 但传 `response_format={"type": "json_object"}`（provider 需要新增可选参数），system prompt 要求严格 JSON。若 JSON parse 失败，做一次二次修复调用（提示模型「上一次输出不是合法 JSON，请重新只输出 JSON」）。
  5. **产出**：
     - `data` = 校验后的 slide_deck JSON。
     - `content` = 通过 `SlideDeckMarkdownSkill` 渲染的 markdown 备用（便于 markdown 下载）。
     - `artifact = AgentArtifact(type="slide_deck", title=<topic>, content=markdown, data=data)`。
     - 若 Bing 未启用，在 warnings 里加 "联网检索未启用（未配置 BING_SEARCH_API_KEY）"。

### 2. Registry / Spec 接入

- `apps/api/app/agents/executors/registry.py`：新增 `if spec.executor_id == "course_iteration": return CourseIterationExecutor(self.chat_provider, self.artifact_repository_factory, self.bing_provider)`。为此把 `AgentExecutorRegistry.__init__` 从只吃 `chat_provider` 扩到再吃 `bing_provider: BingSearchProvider` 和一个 `artifact_repository` 依赖（通过 `Depends` 得到 SessionScope）。
- `apps/api/app/agents/specs.py`：把 `"course_iteration"` 映射进 `executor_id` 字典；`_SYSTEM_PROMPTS["course_iteration"]` 新增 slide_deck 专用长 prompt（含 JSON schema 描述）；`skills` 增加 `("slide_deck_json", "slide_deck_markdown", "artifact_exporter")`。

### 3. Bing 检索集成

- 新目录 `apps/api/app/integrations/search/`：`__init__.py` + `bing.py`。
- 环境变量：`BING_SEARCH_API_KEY`、`BING_SEARCH_ENDPOINT`（默认 `https://api.bing.microsoft.com/v7.0/search`），追加到 `app/core/config.Settings`。
- `SearchResult` dataclass：`available: bool`, `items: list[SearchItem(title, url, snippet)]`。
- `BingSearchProvider.search(query, count=5, mkt="zh-CN")`：`httpx.AsyncClient` GET，超时 6s，异常吞并降级为 `available=False`。
- 单测桩 fixture：`monkeypatch` `_client.get` 返回本地样本 JSON。

### 4. Skills

- `apps/api/app/skills/slide_deck_json.py`：负责校验 & 归一化 LLM 输出：`type/topic/slides` 必填；`slides` 按 `index` 排序；layout 归一化到白名单；不合法直接抛 `AppError("slide_deck_json_invalid")`。
- `apps/api/app/skills/slide_deck_markdown.py`：把 data → markdown（`# {topic}` + 每页 `## {index}. {title}` + bullets + `> 备注:` + 引用列表）。
- `apps/api/app/skills/slide_deck_pptx.py`：`python-pptx` 生成 `.pptx` BytesIO。样式：标题页 slide layout 0，其他用 layout 1（title + content）；对 `layout=two_column` 用 layout 3；`callout` 加一段加粗前缀。

### 5. Artifact 导出扩展

- `apps/api/app/api/artifacts.py`：`export_format` 增加 `pptx`；
  - 分支：`export_format == "pptx"` 且 `artifact.type == "slide_deck"` → `SlideDeckPptxSkill().run(artifact.data)` 返回 `(bytes, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", extension="pptx")`；否则 400。
- `ArtifactExporterSkill` 保持不变（复用现有 markdown/csv）。

### 6. Chat provider 变更

- `ChatProvider.stream_reply(messages, *, response_format=None)`：新增可选形参；实现里若非 None，把 `response_format` 作为 kwargs 加到底层调用；OpenAI-compatible provider 直接支持。默认调用不影响其他 executor。
- 兼容策略：`response_format` 为 `None` 时行为等价现在，不写入 request body。

### 7. 测试

- `tests/agents/test_course_iteration_executor.py`：
  - Bing 未配置时 slide_deck 生成走通、`warnings` 含降级提示。
  - Bing 配置（mock）时 `industry_updates` / `job_skill_focus` 至少 1 条。
  - JSON 首次非法 → 修复重试成功。
  - 追问输入时 `context_signals` 会包含上一版 artifact 的 topic 引用。
- `tests/skills/test_slide_deck_pptx.py`：给定 fixture data，`bytes[:2] == b"PK"`（zip magic），Slides 数量匹配。
- `tests/api/test_artifacts_export.py`：新增 pptx 导出 200 + Content-Type 校验。

## 前端

### 1. 类型 & api

- `apps/web/src/api.ts`：`Artifact.type` 允许 `slide_deck`；`exportArtifact(token, id, format: 'markdown'|'csv'|'pptx')` 支持 `pptx`。
- 无需新接口，走既有 `/api/artifacts/{id}/export?format=pptx`。

### 2. SlideDeckPreview 组件

- 新文件 `apps/web/src/components/SlideDeckPreview.tsx`。
- Props：`artifact: Artifact`, `onExport(format)`, `onCopy(content)`。
- 结构：
  - 顶部工具条：主题 + 页数 + 「下载 PPTX / 下载 MD / 复制 JSON」。
  - 左侧固定宽度缩略图列表（`w-40`，可滚动）。
  - 右侧大图：当前页标题、layout 分支渲染（title / bullets / two_column / callout / summary）；底部 speaker notes 折叠区。
  - 引用条：显示 `citations` 与顶部 `sources` 里对应的可点击链接。
- 键盘 ← / → 翻页；点击缩略图跳页；页码显示 `n / total`。

### 3. TeacherWorkspace 渲染接入

- 参考现有 `isLearningAnalysisArtifactMessage` 判断，新增 `isSlideDeckArtifactMessage`：`msg.metadata` 里有 `type === 'slide_deck'` 即真。
- 中间对话区消息渲染分支：若 `isSlideDeckArtifactMessage` → 渲染 `SlideDeckPreview`，对应 `artifact` 通过 `[...artifacts].reverse().find((a) => a.type === 'slide_deck' && msg.metadata.some(m => m.artifact_id === a.id))` 取出（新版本会取最新）。
- `HistoryDetailModal` 里：`artifact.type === 'slide_deck'` → 渲染 `SlideDeckPreview`，与学情图表并列。

### 4. 追问语义

- 前端不新增按钮或规则；用户后续在同一 conversation 输入的任何消息，正常走 `sendMessage`。后端 executor 会根据消息内容再次判定 slide_deck 分支，`ArtifactRepository.latest_by_conversation` 拿到上一版，做整份重生成。
- 前端在 SlideDeckPreview 顶部加一条提示文字：「在对话框输入修改意见，AI 会整份重生成幻灯」。

## 数据流 / 兼容性

- 现有 course_iteration 会话不打破：无关键词命中时仍走 `GenericChatExecutor`。
- 上一版 slide_deck artifact 保留在数据库，历史聚合面板中已可点开预览。
- `.pptx` 导出为纯二进制，前端下载走 `Blob` 保存，与既有 markdown/csv 路径类似（只是 media_type 改）。

## 回滚点

1. `apps/api/app/agents/executors/course_iteration.py` — 新文件，删除即回退到 GenericChat。
2. `apps/api/app/integrations/search/bing.py` — 未接入前 executor 不会调用，删除即可。
3. `apps/api/app/skills/slide_deck_*.py` — 独立 skill，可整包移除。
4. `apps/web/src/components/SlideDeckPreview.tsx` — 独立组件，导入点仅在 TeacherWorkspace。
5. `ChatProvider.stream_reply` 的 `response_format` 参数默认 None，其他 executor 无感。

## 测试策略

- 后端：pytest 覆盖 slide_deck happy path、Bing 降级、JSON 修复重试、pptx 生成、导出接口 200。
- 前端：`npm run lint` + `npm run build`；浏览器手动验证：
  - 触发生成 → SlideDeckPreview 出现 → 翻页正确。
  - 追问「压缩到 6 页」 → 新版本替换预览，历史保留旧版。
  - 「下载 PPTX」→ 得到 `.pptx`，PowerPoint 打开无损。
  - 无 Bing key 场景下不 crash。
