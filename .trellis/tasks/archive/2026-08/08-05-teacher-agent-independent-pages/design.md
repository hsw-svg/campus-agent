# 技术设计：课堂互动与课程迭代独立页面

## 目标与边界

本设计只覆盖教师工作台中 `course_id === null` 的独立 `classroom_interaction` 和 `course_iteration` 任务。课程上下文不进入新的页面状态模型：课程级任务、课程级智能体历史聚合、`TeacherAgentHistoryPanel` 的课程筛选与 `HistoryDetailModal` 的课程历史详情保持现有行为。

## 页面状态模型

复用 `TeacherWorkspace` 已有的独立智能体状态，不另建全局状态或第二份会话状态：

- `activeStandaloneAgentId`：当前独立智能体，包含 `learning_analysis`、`classroom_interaction`、`course_iteration`。
- `preparingAgentId`：当前是否处于该独立智能体的准备页。
- `standaloneAgentHome`：当前独立智能体是否显示首页；首页为历史列表和“新建任务”入口，详情页为当前会话的 artifact 展示。
- `pendingConversationId`：点击历史记录后等待 `conversations` 当前上下文完成，再调用现有 `openConversation` 恢复会话。

现有学情分析状态可以迁移到同一套通用判断，但必须保持其现有恢复、返回和重新分析语义不变。

## 数据流与历史边界

1. 首页历史只从 `conversations` 读取，不新增 API。筛选条件为 `course_id === null`，且 `agent_id` 属于当前独立智能体；课程迭代额外兼容 `lesson_design` 作为同一独立入口的历史别名。
2. 点击首页历史项后，清空当前运行态并设置 `activeStandaloneAgentId`，通过 `pendingConversationId` 触发现有 `openConversation`。`openConversation` 继续负责恢复消息、附件、artifact 和路由信息。
3. 详情页的 artifact 只从当前 `activeConversationId` 对应的 `artifacts` 中选择，并按独立智能体允许的 artifact 类型过滤：课堂互动使用活动包、课堂观察、课后总结；课程迭代使用 `course_iteration`、`slide_deck`、教案、题目和测验相关类型。禁止跨会话复用上一次结果。
4. 首页新建任务进入现有 `TeacherAgentPreparationPanel`；提交流程仍调用 `startPreparedTask`，不修改请求 payload、workflow ID、文件上传或 SSE 逻辑。任务启动后切换到当前独立详情页。
5. 左侧通用任务列表通过统一的独立 Agent 会话判定排除全部无课程独立任务；会话仍保留在 `conversations` 数据源中，供对应 Agent 首页历史和成果恢复使用。
6. SSE 生成器外层捕获 `asyncio.CancelledError`，将已创建的 AgentRun 标记为 `failed/stream_cancelled` 后继续传播取消，避免前端重试门禁被永久 `running` 状态锁住。
7. `CourseIterationExecutor` 的普通文本分支保留现有模型调用和引用，但把返回文本包装为 `course_iteration` Markdown Artifact；幻灯关键词分支继续返回既有 `slide_deck`，不改变 PPTX schema。
8. 对修复前的历史兼容以读取时降级完成：当前会话没有允许类型的 Artifact、但存在 assistant 文本时，详情页展示“历史文本成果”。不回填数据库，避免把不可验证的旧消息伪装成结构化 Artifact。

## 渲染结构

独立智能体页面使用与学情分析相同的页面级覆盖层，统一为：

```text
独立智能体页面
├─ 固定关闭按钮
├─ 标题与简介（无“教师 Agent · …”副标题、无左侧 Logo）
├─ 首页：新建任务卡片 + 历史记录列表
└─ 详情页：返回首页 + 摘要 + artifact 内容 + 复制/导出操作
```

课堂互动和普通课程迭代的详情内容优先复用已有 `Markdown`、复制和导出逻辑；课程迭代的 `slide_deck` 复用 `SlideDeckPreview` 及其 PPTX/Markdown 导出。不把通用聊天消息、输入框或课程历史面板嵌入独立页面。学情分析继续使用现有 `LearningAnalysisReport` 专用渲染，不改变报告契约。

准备页继续使用现有表单字段和校验，仅调整独立准备页的顶部视觉，使其与独立首页/详情页一致；课程级工作流不引用该页面状态。

## 兼容性与风险控制

- 不修改 API 类型、数据库、`slide_deck` schema 或课程级历史 API；只补齐普通课程迭代已有 `AgentResult` 的 Artifact 输出。
- 不改变 `TeacherAgentHistoryPanel` 的 props、分组、课程过滤、删除和课程级弹窗回调。
- `HistoryDetailModal` 保留作为课程级/其他历史记录的现有展示入口；只有独立首页自己的无课程历史项绕过它。
- 独立页面的唯一滚动容器由页面外层持有，详情内部避免新增嵌套滚动；动画遵守 `useReducedMotion`。
- 状态切换统一清空 `pendingConversationId`、当前独立详情和运行态，避免在智能体切换或新建任务时闪回旧 artifact。
- 历史点击与 `onStarted` 都显式把首页状态设为 `false`；只有进入 Agent、返回首页时才设为 `true`，避免同一布尔值在相反导航意图间写反。

## 可回滚点

主要改动集中在 `apps/web/src/components/TeacherWorkspace.tsx` 与 `apps/web/src/components/TeacherAgentPreparationPanel.tsx`。若详情渲染出现问题，可回退通用独立页面分支，保留现有 `TeacherAgentHistoryPanel`、`HistoryDetailModal` 和课程工作流代码不变。
