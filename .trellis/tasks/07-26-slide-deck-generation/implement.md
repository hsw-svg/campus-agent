# 实施计划

## Ordered Checklist

1. [x] 后端：新增 `Settings.bing_search_api_key` / `bing_search_endpoint`，以及 `integrations/search/bing.py`（含单测桩）。
2. [x] 后端：`ChatProvider.stream_reply` 增加可选 `response_format` 参数，改动最小、默认行为不变。
3. [x] 后端：新增 `skills/slide_deck_json.py`（校验/归一化）与 `skills/slide_deck_markdown.py`（渲染 markdown）。
4. [x] 后端：新增 `skills/slide_deck_pptx.py`（`python-pptx` 渲染，标题/bullets/two_column/callout/summary layout）。
5. [x] 后端：新增 `agents/executors/course_iteration.py`，串联 Bing、上一版 artifact、chat_provider、skills，产出 slide_deck artifact。
6. [x] 后端：`executors/registry.py`、`agents/specs.py` 接入 course_iteration，Registry 依赖注入拓宽以获取 Bing provider 与 artifact repository。
7. [x] 后端：`api/artifacts.py` 增加 `format=pptx` 分支；接口签名保持不变，仅扩枚举。
8. [x] 后端：`apps/api/pyproject.toml` 加 `python-pptx` 依赖，root `.venv` 安装。
9. [x] 后端测试：`test_course_iteration_executor.py`（含 Bing on/off、JSON 修复）、`test_slide_deck_pptx.py`、`test_artifacts_export.py` 新增 pptx 用例。
10. [x] 前端：`SlideDeckPreview.tsx`（左侧缩略图 + 右侧大图 + 工具条），支持键盘翻页。
11. [x] 前端：`TeacherWorkspace.tsx` 中间对话区与 `HistoryDetailModal` 接入 `SlideDeckPreview`；`isSlideDeckArtifactMessage` 判断；`exportArtifact` 支持 `pptx`。
12. [x] 前端：`Artifact` 类型允许 `slide_deck`；预览器顶部提示「输入修改意见触发整份重生成」。
13. [x] 端到端手测：无 Bing key 场景 → 有 Bing key 场景 → 追问重生成 → 下载 pptx；`npm run lint` / `npm run build` / `pytest` 全绿。

## Validation

- `cd apps/api && ../../.venv/Scripts/python.exe -m pytest`
- `cd apps/web && npm.cmd run lint && npm.cmd run build`
- 浏览器：教师工作台创建 course_iteration 会话，输入「围绕 xx 生成 10 页课件」→ 预览、翻页 → 追问「压缩到 6 页」→ 新版本 → 「下载 PPTX」PowerPoint 打开正常。

## Risky Files / Rollback Points

- `apps/api/app/agents/executors/registry.py`：注入依赖变化，可能影响其他 executor 构造；先本地 pytest 覆盖。
- `apps/api/app/integrations/llm/providers.py`：`response_format` 新增，需保证兼容非 OpenAI-compatible provider（若有）。
- `apps/api/app/skills/slide_deck_pptx.py`：外部二进制格式，用 pytest 校验 zip magic 与页数。
- `apps/web/src/components/TeacherWorkspace.tsx`：改到消息渲染与弹窗，注意与已有 `LearningAnalysisReport` 分支互不打架。

若 executor 依赖注入影响过大，可先把 Bing / ArtifactRepository 通过 lazy factory 从 request 上下文获取，避免动 registry `__init__` 签名。
