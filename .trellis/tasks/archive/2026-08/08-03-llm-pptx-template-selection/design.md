# 技术设计

## 1. 目标与边界

本任务在现有 `course_iteration -> slide_deck Artifact -> PPTX export` 链路内增加两项能力：

1. 在受控的“AI科技 / 商业计划书”模板集合中选择模板，并把结果固化到 Artifact。
2. 导出时复制模板中的真实源页面，按登记的对象槽位替换文字，保留源模板的母版、布局、背景和装饰。

本期只处理文字，不新增前端模板管理、在线上传、图片替换、图表生成或第三方演示文稿同步。两份当前模板仅用于开发验证，许可状态登记为 `development_only`，但不增加运行时硬性禁用。

最终模板视觉本期只通过下载 PPTX 查看，不增加 PPTX 转 PNG、服务端截图或图片预览链路。现有前端结构化内容预览保持兼容；前端直接预览 PPTX 留给后续独立任务。

## 2. 当前问题

- `apps/api/app/skills/slide_deck_pptx.py` 通过 `_THEME_KEYWORDS` 做关键词匹配，不是 LLM 语义选择。
- 当前导出器用 `presentation.slides.add_slide(layout)` 从空布局创建页面；两份新模板的大量设计位于源页面本地对象中，空布局不能还原这些设计。
- 当前导出器始终额外添加封面，而生成 JSON 通常已经包含 `layout=title` 的第一页，造成预览和下载页数不一致及重复封面。
- 模板中包含示例主题、演讲人、网址和授权说明页；不能通过“清空所有文本框”的宽泛规则处理，否则会误删需要保留的视觉文字。

## 3. 模块划分

### 3.1 模板目录与注册表

在 `apps/api/app/skills/pptx_templates/` 内增加受控注册模块与对象映射清单：

- `catalog.py`
  - `PptxTemplateSpec`：`id`、`display_name`、`description`、`file_name`、`license_scope`、`frames`。
  - `PptxFrameSpec`：`id`、`source_slide`、支持的逻辑 layout、容量、可编辑对象映射。
  - 只允许注册表中的文件名；不接受 LLM 或用户提供的任意路径。
- `manifests/ai_tech.json`
- `manifests/business_plan.json`

每个 frame manifest 必须分类源页面上所有含文字对象：

- `rewrite`：绑定到 `title`、`subtitle`、`body`、`item_n_title` 等语义字段。
- `delete`：示例署名、示例网址或不适用于输出的说明文字。
- `keep`：明确属于视觉系统且允许保留的固定文字。

对象优先以源幻灯片内稳定 `shape_id` 定位，并记录 shape name 作为审计信息。组合图形递归查找子对象。未分类的可见示例文字使 manifest 验证失败。

### 3.2 模板选择

模板选择在 `apps/api/app/agents/executors/course_iteration.py` 中完成，并与现有课件 JSON 生成共用一次 LLM 调用，不增加额外网络往返。

选择优先级：

1. `_find_explicit_template_id(request.content)` 命中“AI科技”或“商业计划书”时强制使用该模板。
2. 未明确指定且上一版 Artifact 有合法 `template_id` 时沿用上一版。
3. 首次生成且未指定时，把受控模板的 `id/name/description` 注入 prompt，让 LLM 在生成课件 JSON 时同时返回顶层 `template_id`。
4. LLM 返回未知、空或非法 ID 时回退 `ai_tech`。

解析后由后端覆盖并写入稳定元数据，不信任模型自行填写名称或许可：

```json
{
  "template_id": "ai_tech",
  "template_name": "AI科技",
  "template_selection_source": "explicit|previous|llm|fallback",
  "template_license_scope": "development_only"
}
```

`SlideDeckJsonSkill` 保留并规范化 `template_id` 字符串；最终白名单校验和元数据补全由 catalog resolver 负责。

### 3.3 页面规划

`SlideDeckPptxSkill` 先把结构化页面映射成 frame plan：

- 第一页为 `title`：直接使用 cover frame，不额外添加封面。
- 第一页不是 `title`：根据顶层 `topic/audience/objective` 合成一页 cover，再映射全部结构化页面。
- `two_column`：只匹配具有两组标题/正文槽位的 frame。
- `bullets`：按 bullet 数量和字符容量选择通用内容 frame。
- `callout`：选择强调页或章节式 frame。
- `summary`：优先选择总结/结束 frame；若不是末页则使用通用总结 frame。

同一 frame 可以重复使用，但在存在其他适配 frame 时不得与上一内容页连续重复。选择过程确定性运行，便于测试；LLM 不直接指定源幻灯片编号或 shape ID。

首期候选源页面基于结构审计确定，实施时通过 manifest 验证再最终收敛：

- AI科技：封面 1、目录 3、章节 4/8/12/20、通用文字内容 6/7/15/18/19/23、结束 31。
- 商业计划书：封面 1、目录 2、章节 6/13、通用文字内容 4/7/8/10/12/14/17/19、结束 20。

含强主题截图、工具 Logo、原始数据图、授权说明的页面不进入 frame catalog。

### 3.4 源页面复制

为准确保留页面本地设计，新增纯内存 OOXML 复制器：

1. 以所选模板 PPTX ZIP 包为基底读取所有部件。
2. 按 frame plan 将源 `ppt/slides/slideN.xml` 和对应关系文件复制为顺序输出页面。
3. 保留源页面到 layout/master/theme/media 的关系；去除源 notesSlide 关系，避免多个输出页共享同一备注页。
4. 重写 `ppt/presentation.xml`、`ppt/_rels/presentation.xml.rels` 和 `[Content_Types].xml` 的幻灯片清单，只保留输出页面；源模板中的其他页面不进入结果。
5. 用 `python-pptx` 打开内存中的 starter deck，按 manifest 精确替换/删除文字并写入本次 notes，最后保存到 `BytesIO`。

复制器不从外部路径取资源，不修改源模板文件，也不把多个模板视觉混在同一份课件中。

### 3.5 文本填充与样式保留

- 替换文字时复用源对象的字体、字号、颜色、对齐、内边距和段落格式。
- 单文本框多段内容以源首段/首 run 为格式样板；不使用 `shape.text = ...` 直接重置全部格式。
- manifest 为每个字段声明 `max_chars`/`max_items`。Prompt 同时约束 LLM 输出长度。
- 超限时优先选择容量更大的同类 frame；仍超限时做确定性压缩/省略并保留完整内容在 speaker notes，不通过缩小字体或覆盖装饰兜底。
- 每个输出页面的原 notes 与模板教学备注不保留，只写入 `slides[].notes`、多媒体建议及必要的内容压缩说明。

## 4. 数据兼容

- 数据库结构不变，`Artifact.data` 继续使用 JSON；无需 Alembic 迁移。
- 历史 `slide_deck` 没有 `template_id` 时导出回退 `ai_tech`。
- 前端只读取既有课件字段，新增顶层模板元数据不会破坏 `SlideDeckPreview`；本期不需要前端改动。
- 前端不接收 PNG 或渲染产物，也不新增预览接口；下载仍是查看最终模板样式的唯一方式。
- 导出 API 路径、查询参数、Content-Type 和下载行为保持不变。
- 原四份空壳模板不再参与选择，但先不删除，避免把清理动作与功能改造混在同一提交。

## 5. 失败与回退

- 明确模板名：强制对应 ID。
- 无效/模糊模板名：进入 LLM 自动选择。
- 无上一版、LLM ID 无效：回退 `ai_tech`。
- Artifact 指定模板文件缺失、manifest 无效或对象定位失败：抛出稳定 `AppError`，禁止静默回退到空白 PPT，因为静默回退会重新产生“简陋课件”。
- 历史 Artifact 无模板字段不是错误，按兼容规则使用 `ai_tech`。

## 6. 验证策略

- Catalog：两个 ID、名称别名、默认项、许可状态和文件存在性。
- 选择：显式名称、首次 LLM、上一版沿用、显式切换、非法 ID 回退。
- Manifest：源页存在、shape ID 存在、文字对象分类完整、容量合法、禁用授权说明页。
- 页面规划：逻辑 layout 映射、首张 title 不重复、无 title 时补封面、重复 frame 不连续。
- PPTX：ZIP 可打开、可被 `python-pptx` 重新读取、输出页数、模板页面尺寸、母版/布局关系、目标文字存在、示例文字不存在、notes 独立；不把 PNG 渲染作为本期验收门槛。
- API：现有导出 Content-Type/Content-Disposition 保持兼容。

## 7. 风险与回滚

- OOXML 关系复制是最高风险点；通过小型复制器、关系级单测和用 `python-pptx` 重新打开结果来约束。
- 模板对象 ID 若在人工编辑模板后变化，manifest 验证应立即失败并指出模板/frame/shape，而不是生成半成品。
- 回滚时可恢复 `SlideDeckPptxSkill` 的旧实现；新增 Artifact 字段为可选，不需要数据迁移或回滚数据库。
- 两份模板未获分发授权，比赛提交前必须替换；注册表的文件名、对象映射和 `license_scope` 是唯一需要替换的模板层配置。
