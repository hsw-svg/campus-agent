# 智能 PPT 生成与预览

## 背景

教师使用 `course_iteration` 智能体希望一次性拿到「可展示的教学幻灯」，而不是散文式的教学建议。当前 agent 只输出 markdown 文档，需要教师手动搬到 PowerPoint。本任务在教师工作台中新增智能 PPT 生成链路：教师给出课程主题 → agent 综合课程上下文（学情、互动、批改）与实时联网信息 → 产出结构化幻灯，可逐页预览、追问修改、并导出 `.pptx`。

## 目标用户

教师角色（`teacher`）在教师工作台内的 `course_iteration` 会话中使用。

## 用户故事

- 输入「围绕『Python 切片与元组』生成 12 页课件」，收到结构化 slide_deck 并逐页预览。
- 中间对话区看到幻灯预览：缩略图列表 + 当前页大图，可翻页 / 跳页。
- 追问「第 3 页加一个真实项目案例」「整体压缩到 8 页」，agent **整份重生成**并替换预览。
- 一键下载 `.pptx`。
- 幻灯自动带「重点」「行业应用」「岗位技能」标注，让老师信任已参考学情/互动/批改与 Bing 联网信息。

## 范围

### 首版必做

1. 后端：新增 artifact 类型 `slide_deck`（`format=json`），`data` 为结构化 JSON，`content` 存 Markdown 备用。
2. 后端：`course_iteration` agent 增加「slide_deck」分支——识别到生成 PPT 意图后，聚合课程内 `learning_analysis / classroom_summary / grading` 摘要 + 上一版 slide_deck（如有）作为上下文，调用 chat 模型输出结构化 JSON。
3. 后端：`integrations/search/bing.py`——包 Bing Web Search v7，读取 `BING_SEARCH_API_KEY` + 可选 `BING_SEARCH_ENDPOINT`；agent 每次现搜「主题 + 行业最新案例」「主题 + 岗位技能」两类查询；未配置 key 时优雅降级，结果为空 + warning。
4. 后端：`GET /api/artifacts/{id}/export?format=pptx`——`python-pptx` 将 slide_deck JSON 渲染成 `.pptx` 下载。
5. 前端：`SlideDeckPreview` 组件——横向翻页 + 缩略图列表 + 当前页大图，展示标题、要点、演讲者备注、引用、重点标记；中间对话区（消息渲染）与 `HistoryDetailModal` 都复用。
6. 前端：SlideDeckPreview 顶部「下载 PPTX / 下载 MD / 复制 JSON」按钮。
7. 前端：追问输入沿用现有输入框，用户消息自然进入同一 conversation，agent 感知最近一次 slide_deck artifact 做整份重生成。

### 显式不做（二期）

- 单页增量修改（只支持整份重生成）。
- 图片素材（首版全文字 + 结构化 bullets）。
- 主题皮肤（一套默认样式）。
- 幻灯图表可视化（用 bullets / 表格描述即可）。
- 与 Google Slides / 腾讯文档打通。

## 输入 / 输出契约

`slide_deck.data` JSON schema（首版）：

```json
{
  "topic": "Python 切片与元组",
  "audience": "计算机学院大二",
  "objective": "掌握切片语法与元组不可变性",
  "duration_minutes": 45,
  "context_signals": {
    "learning_analysis": "…摘要…",
    "weak_points": ["切片负步长", "元组内可变元素"],
    "classroom_summary": "…",
    "grading": "…",
    "job_skill_focus": ["Python 中级工程师岗要求：面向对象与内置数据结构"],
    "industry_updates": [
      {"title": "…", "url": "https://…", "snippet": "…"}
    ]
  },
  "slides": [
    {
      "index": 1,
      "layout": "title",
      "title": "Python 切片与元组",
      "subtitle": "面向大二·45 分钟",
      "bullets": [],
      "notes": "开场 3 秒抢答",
      "key_points": [],
      "citations": []
    },
    {
      "index": 2,
      "layout": "bullets",
      "title": "为什么这节课重要",
      "bullets": ["岗位面试常考", "承接后续 numpy 广播"],
      "notes": "…",
      "key_points": ["面试高频"],
      "citations": [{"title": "Real Python 切片教程", "url": "https://…"}]
    }
  ],
  "sources": [
    {"title": "…", "url": "https://…", "snippet": "…"}
  ]
}
```

- `layout` 允许值：`title | bullets | two_column | callout | summary`；pptx 渲染时未知 layout 回退到 `bullets`。

## 验收标准

1. 教师在 course_iteration 会话内触发 slide_deck 生成，中间对话区渲染 `SlideDeckPreview`，翻页正常；`HistoryDetailModal` 中同样可预览。
2. 未配置 `BING_SEARCH_API_KEY` 时接口不崩，`industry_updates` 为空数组，artifact status_message 或响应 warning 提示「联网检索未启用」。
3. 配置 Bing key 后，`industry_updates` 与 `job_skill_focus` 至少各 1 条，`slides[].citations` 至少引用其中一条来源。
4. 追问「压缩到 6 页」「第 3 页改成案例讲解」触发整份重生成，SlideDeckPreview 显示新版本；旧版本保留在智能体历史聚合中可回看。
5. 「下载 PPTX」返回可被 PowerPoint 打开的 `.pptx`，包含标题页与每页 bullets/notes。
6. `apps/web` `npm run lint` / `npm run build` 通过；`apps/api` `pytest` 通过（含 slide_deck 生成正常路径 + Bing 降级路径 + pptx 导出路径）。

## 依赖 / 风险

- 需要 `BING_SEARCH_API_KEY`，用户运行时提供；本地测试用 mock。
- `python-pptx` 新增到 `apps/api/pyproject.toml`。
- Chat 模型返回严格 JSON 的稳定性：使用 `response_format=json_object` 且做兜底 parse + 一次重试。
- Slide 生成延迟：Bing 搜索 + LLM 输出可能 15-40s；前端沿用现有 SSE 打字 + tool_status 提示，不改协议。
