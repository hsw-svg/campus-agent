# P1 扩展能力技术设计

## 1. 设计目标与事实来源

本设计只覆盖第一交付切片：学生 `course_qa`、`personal_tutor`，行政 `meeting_minutes`、`todo_breakdown`，以及它们共用的当前任务资料选择、Artifact 展示/导出和隔离反馈。

仓库代码是技术栈事实来源：后端采用 FastAPI/Pydantic/SQLAlchemy，前端采用 React 19 + TypeScript + Vite + Tailwind CSS，当前没有 Vue、Pinia、Element Plus 或 Vitest 测试脚本。本轮不会按过时文档重写前端，也不会为了文档中的旧测试命令引入新的测试框架。

## 2. 边界与交付顺序

父任务拆为三个子任务：

1. `p1-student-admin-executors`：先稳定后端 AgentSpec、契约、Executor、Artifact 数据结构和隔离测试。
2. `p1-context-artifact-frontend`：消费稳定的 agent/artifact 契约，补齐 React 资料选择、引用、结果卡、导出和错误恢复。
3. `p1-docs-stack-alignment`：根据最终实现修正开发、设计、前端、UI 提示和项目规范文档。

子任务不是隐式依赖；依赖关系写入各自 PRD/执行计划。先启动后端子任务，后端契约稳定后启动前端子任务，最后完成文档同步。

## 3. 后端设计

### 3.1 AgentSpec 与 Executor

保留 `apps/api/app/agents/registry.py` 的角色白名单作为入口，扩展 `apps/api/app/agents/specs.py` 的配置映射：

- `course_qa`：student，必须明确选择当前学生工作空间课程资料；默认排除学情明细。
- `personal_tutor`：student，必须明确选择当前学生工作空间错题/作业/自述资料；默认排除学情明细。
- `meeting_minutes`：admin，内容可以来自当前消息，也可以补充明确选择的当前行政资料；不能读取其他工作空间。
- `todo_breakdown`：admin，内容可以来自当前消息，也可以补充明确选择的当前行政资料；输出待办时不得补造事实。

为每个 agent 配置独立 prompt、输入字段、允许资料范围和 `executor_id`。Executor 放在实际代码的角色子目录中：

```text
apps/api/app/agents/
  student/course_qa.py
  student/personal_tutor.py
  admin/meeting_minutes.py
  admin/todo_breakdown.py
  p1_contracts.py
```

四个 Executor 可共享“调用模型并解析结构化 JSON”的小型内部辅助函数，但每个 Executor 必须保留独立 prompt、输入校验、输出类型和 Artifact 类型，不能继续回落到通用聊天。

### 3.2 结构化输出契约

使用 Pydantic 模型配合现有 `app.core.json_guard.parse_json()`，禁止自动修复无效 JSON。建议稳定的最小数据形状：

- `course_qa`：`answer`、`key_points[]`、`follow_up_questions[]`。
- `personal_tutor`：`diagnosis`、`explanation`、`mistakes[]`、`practice[]`、`follow_up_questions[]`。
- `meeting_minutes`：`topics[]`、`decisions[]`、`action_items[]`；每个决议/待办的负责人和日期允许为空，模型只能输出输入中有依据的事实。
- `todo_breakdown`：`items[]`；每项至少包含 `task`，可选 `owner`、`due_date`、`priority`、`evidence`。

解析失败返回 `invalid_structured_output`，不保存成功 Artifact；输入缺失返回 422 `agent_input_incomplete`；模型或网络失败沿用现有失败/重试路径。成功结果创建一个 Artifact，`type` 使用稳定的 agent-specific 值，`data` 保存结构化对象，`content` 保存可读 Markdown，`format` 为 `markdown`。

### 3.3 ContextPolicy 与隔离

继续由 `ContextBuilder` 负责资源归属、显式选择、检索和引用来源：

- 学生 agent 的 selected attachment 必须属于当前 student workspace；没有选择资料时在模型调用前返回 `needs_input`。
- 行政 agent 的当前消息是直接输入；如果使用附件，附件必须显式选择且属于当前 admin workspace。
- 所有非学情 agent 过滤 `is_learning_analysis_material`，不把教师学情表的行级内容放入 Prompt 或来源。
- selected Artifact 继续通过 `ArtifactRepository.list_selected_for_conversation()` 校验 workspace 和 conversation；不得跨会话/跨空间引用。
- `AgentRequest`、`AgentRun` 和 SSE 中保留实际归一化的 selected ids，引用只来自 `AgentResult.citations`。

### 3.4 SSE、重试与 Artifact

复用 `stream_assistant_reply()` 的统一流程。成功时发出 `delta`、`artifact`、`done`，失败时保留用户消息和 AgentRun 状态；`retry` 复用原始 selected ids。来源事件与现有 `artifact`/`sources` 兼容，前端另行收集为 citations，不把上传状态当成实际引用。

`ArtifactExporterSkill` 继续提供 Markdown/CSV；CSV 对嵌套结构使用 JSON 字符串，确保四种 P1 结果无需各自实现导出器。文件名和 Content-Type 由公共 Artifact API 统一处理。

## 4. 前端设计（实际 React 代码）

### 4.1 资料上下文

复用 `useWorkspaceChat` 已有的 `selectedAttachmentIds`、`selectedArtifactIds`、`toggleAttachment`、`toggleArtifact` 和 `streamMessage` 参数，新增/提取可复用 React 组件展示：

- 工作区资料库与当前对话附件分组；
- 当前任务可选 Artifact；
- 已选择的资源数量和“本次请求只会使用已选资源”提示；
- 当前 Executor 返回的 citations，而不是所有上传文件。

切换角色、打开/新建/删除对话继续清空选择状态。组件不得自行判断资源权限、计算成绩或改变后端返回的来源。

### 4.2 结果和状态

扩展 `ArtifactCard` 的通用分支，以 agent-specific data 渲染四种 P1 结果，保留复制、Markdown/CSV 导出；不能用工作区静态模拟数据替代 API 返回。

Student/Admin workspace 接入：

- P1 agent 选择或路由信息；
- `needs_input`/`failed`/`retry`/`degraded` 的中文可操作提示；
- 资料选择器和 Artifact 选择器；
- 结构化结果卡和真实引用来源。

当前包没有 Vitest 测试命令，验证采用 `npm run lint`（TypeScript）和 `npm run build`，并保留可执行的浏览器/演示冒烟路径。

## 5. 文档对齐设计

实现完成后同步：

- `docs/开发文档.md`：React 技术栈、3000 开发端口、8080 Docker 入口、当前 P1 进度和实际验证命令。
- `docs/设计方案.md`：React 工作台架构和已交付 agent/artifact 契约。
- `docs/前端开发文档.md`：React 组件/Hook/useState 目录和 TypeScript/build 验证，不再描述 Vue/Pinia/Element Plus。
- `docs/UI设计提示词.md`：将实现提示改为 React + Tailwind CSS + lucide-react/Motion 可实现范围。
- `AGENTS.md`：项目规范中的前端技术栈、端口和验证命令与代码一致。

只把已实现的内容标记为完成；未实现的教师 P1 留在后续规划，不通过文档措辞提前宣称完成。

## 6. 兼容性、风险与回滚

- 不新增数据库表；Artifact/AgentRun 现有 JSON 字段足以承载本轮结构化结果。
- P1 agent 注册错误或结构化解析错误可独立回滚到旧的 generic fallback，但验收时不允许以 fallback 作为完成标准。
- 前端可先保留现有 Student/Admin 静态面板，再逐块插入真实资源/结果组件，避免重写完整视觉布局。
- 保留用户当前未提交的 `AGENTS.md`、`CLAUDE.md` 变更，不在本任务中重置或覆盖。
