# 教师独立智能体入口技术设计

## Architecture

本任务保持现有教师工作台、Conversation、AgentRun、SSE 和 Artifact 架构，仅增加一个教师独立 Agent 准备层和一条受控提交路径。

```text
教师侧栏固定入口
  -> TeacherAgentPreparationPanel（尚未创建会话）
  -> 校验表单并暂存 File 对象
  -> useWorkspaceChat.startPreparedTask
       1. POST /conversations（course_id = null）
       2. 上传暂存文件为 conversation scope
       3. 调用现有 message stream（显式 agent_id + workflow_id）
  -> 复用 TeacherWorkspace 现有消息流、结构化成果卡和导出/预览
```

不创建新的数据库表、Agent、执行器或专用流式 API。三个入口分别映射到既有 Agent：

| 入口 | Agent ID | 最低输入 | 可选输入 |
| --- | --- | --- | --- |
| 学情分析 | `learning_analysis` | 匿名表格 | 分析关注点 |
| 课堂互动 | `classroom_interaction` | 教学主题、教学目标 | 时长（默认 45 分钟）、资料 |
| 课程迭代 | `course_iteration` | 教学主题、迭代目标 | 资料 |

## Frontend Boundaries

### Sidebar and selection state

- `TeacherWorkspace` 将“导航”改为“教师 Agent”，删除“最近会话”按钮并渲染三个固定入口。
- 固定入口只渲染 Agent 图标和名称，使用约 40px 的触控高度；详细描述只保留在准备页上下文中。
- 保留“新建任务”、课程树、课程会话、无课程任务历史和顶部“智能体历史”。
- 新增 `preparingAgentId`（仅允许上述三个 Agent）作为准备页状态。点击入口时：切到工作台、清空当前聊天展示、退出课程上下文并打开准备页；不得发送请求。
- 打开课程、历史会话或普通“新建任务”时退出准备页，恢复各自既有流程。

### Preparation component

新增 `TeacherAgentPreparationPanel.tsx`，集中维护三种表单的共享布局、文件暂存、校验和提交；Agent 元数据使用一个有类型的配置表，避免侧栏和准备页重复名称、说明、图标语义与默认提示模板。

- 文件只保存在组件内的 `File[]`；卸载或刷新自然丢弃。
- 学情分析限制为现有支持的表格扩展名并要求至少一份。
- 课堂互动将主题、目标和最终时长拼成能触发现有互动分支的明确提示；时长空值归一为 45。
- 课程迭代将主题和迭代目标拼成明确提示；附件为空合法。
- 有表单内容或暂存文件时切换入口，使用轻量确认避免误丢；空表单直接切换。
- 准备组件本身不绘制外围卡片边框或嵌入式页头；`TeacherWorkspace` 在 `main` 内用绝对定位覆盖层承载它，层级高于顶部 App Bar 和右侧历史面板。
- 底层工作区保持挂载以便关闭后无损恢复，但在覆盖期间设置 `inert`/`aria-hidden`，并通过半透明背景、较强 backdrop blur 和低对比装饰色弱化。
- 覆盖层以无弹跳的短淡入/轻微缩放进入，退出路径对称；减少动态效果时退化为短淡入淡出。唯一的页面级退出控件位于右上角。
- 页面级退出控件固定在覆盖层右上角，不参与表单排版或滚动；三种准备表单统一从同一顶部基线开始，内部切换不使用纵向位移动画，避免因表单高度不同产生页面跳动。
- 覆盖层的 React key 必须固定，不能使用 `preparingAgentId`；智能体切换只重建带 `preparingAgentId` key 的内部表单。这样磨砂合成层在切换期间始终保持不透明，同时各 Agent 的本地表单状态仍会重置。

### Prepared task orchestration

`useWorkspaceChat` 增加 `startPreparedTask`，内部复用现有流式处理函数而不是复制 SSE 状态机。建议先抽取私有的 `runMessage`/`streamIntoConversation`：

1. 校验 token、内容和忙碌状态。
2. `createConversation(token, null, null)`。
3. 逐个或有界并行调用现有 `uploadAttachment(..., 'conversation')`，收集附件 ID。
4. 任一上传失败时删除刚创建的会话作为补偿回滚，恢复准备页并显示错误，不启动 Agent。
5. 上传成功后，以显式 `agent_id`、收集的附件 ID、空课程 ID和 `teacher-standalone-agent` 工作流标识进入现有 SSE。
6. 一旦 SSE 已开始，失败时保留会话和内容，沿用现有重试/停止行为。

普通 `sendMessage`、课程内自动资料选择和现有上传入口保持兼容。

## Backend Boundaries

新增单一工作流标识 `teacher-standalone-agent`，只用于区分无课程独立 Agent 与普通 `standalone-task`。允许空资料必须同时满足：

- `role == 'teacher'`
- `conversation.course_id is None`
- `workflow_id == 'teacher-standalone-agent'`
- Agent 为 `classroom_interaction` 或 `course_iteration`

### Context policy exception

`ContextBuilder.build` 接收工作流上下文或明确的 `allow_empty_attachments` 判定结果。在上述条件成立时，`course_iteration` 即使没有选中附件也可以构建空资料上下文；其他调用继续执行现有 `requires_explicit_attachments` 校验。附件存在时仍必须显式传 ID并执行现有工作区/会话隔离校验。

### Classroom activity exception

`ClassroomInteractionExecutor._missing_activity_inputs` 在上述独立工作流下仍强制主题和教学目标，但不再强制“课程资料”。提交提示始终包含总时长（默认值由前端补全），执行器继续执行现有时长与结构化输出校验。课程关联对话仍要求资料或学情成果。

### Trust boundary

空资料豁免必须使用服务端已加载的 Conversation `course_id`，不能只信任请求体中的 `course_id`。工作流标识只改变“能否空资料执行”，不扩大附件/Artifact 的读取范围。

## Data and Compatibility

- Conversation 仍以 `course_id = null` 表示独立任务。
- AgentRun 继续记录显式 Agent、`workflow_id`、附件 ID 与 input refs。
- Artifact 仍归属新会话，现有消息恢复通过历史 message `agent_id` 和 Artifact 引用工作。
- 不需要 Alembic 迁移或共享 API 字段变更。
- 课程内三项能力不改变默认资料选择、执行器或结果组件。

## Failure and Rollback

- 表单校验失败：停留准备页，无服务端副作用。
- 会话创建失败：停留准备页并显示错误。
- 附件上传失败：删除本次新建的空/半成品会话；若补偿删除也失败，刷新会话列表并保留可诊断错误，不发送模型请求。
- SSE 失败：保留会话，沿用现有失败状态和重试入口。
- 回滚本功能只需移除固定入口、准备组件、Hook 编排入口及独立工作流空资料例外；现有课程功能无需数据回滚。
