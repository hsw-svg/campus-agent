# State Management

> How state is managed in this project.

---

## Overview

<!--
Document your project's state management conventions here.

Questions to answer:
- What state management solution do you use?
- How is local vs global state decided?
- How do you handle server state?
- What are the patterns for derived state?
-->

当前工作台不引入额外全局状态库。跨组件的会话、附件、SSE 运行状态由
`src/hooks/useWorkspaceChat.ts` 统一协调，组件只接收数据和回调；短暂的展示状态保留在组件内部。

---

## State Categories

<!-- Local state, global state, server state, URL state -->

### Workspace 与 conversation 状态

- `workspaceAttachments` 是工作台资料库，切换新对话时保留。
- `conversationAttachments` 只表示当前对话附件；新建对话不应创建空的后端 conversation。
- `messages`、`isAiTyping`、`runStatus`、`toolStatus` 和 `artifacts` 只能从同一个
  `useWorkspaceChat` 实例读取，不能在右侧功能区另起一套“处理中”或成果状态。
- 组件可维护弹窗开关、折叠状态、当前勾选项等局部 UI 状态，但不能复制运行状态。

---

## When to Use Global State

<!-- Criteria for promoting state to global -->

### 单任务源、双视图

一次用户意图只允许创建一次执行请求。提交前由 hook 按以下字段生成临时签名并阻止重复提交：

```ts
const requestSignature = [
  content,
  ...requestAttachmentIds.slice().sort(),
  ...selectedArtifactIds.slice().sort(),
].join('|')
```

中间对话区负责执行叙事、消息流和完整 `ArtifactCard`；右侧功能区负责参数选择、执行入口、
运行摘要和成果索引。右侧成果索引只能引用中间区成果，不得再次渲染完整成果详情。

### 课程任务的资料默认值

- 教师工作台的课程任务不在右侧显示资料勾选器；`useWorkspaceChat` 将当前课程可见的工作区资料与当前
  对话附件合并为 `requestAttachmentIds`。
- 首次发送可能发生在资料库请求完成前，因此后端也必须将课程任务的空 `selected_attachment_ids` 解析为全部
  课程可见资料；这不是教师端的静态勾选状态。
- 无课程的独立任务和学生/行政工作台继续使用 `selectedAttachmentIds` 的显式选择语义，避免把课程默认规则
  扩散到其他角色。

---

### 课程上下文驱动的快捷入口

与当前课程相关的快捷任务文案和提示词属于派生 UI 状态，应从 `activeCourse` 或 `courseContext` 通过一个纯函数
集中生成，再由欢迎区、报告操作区和输入区等多个入口共同消费。不要在各个 JSX 区域分别保存相同的静态 prompt，
也不要为首屏文案单独增加一次课程推荐请求。

```tsx
const quickActions = useMemo(
  () => buildTeacherQuickActions(activeCourse?.name ?? null),
  [activeCourse?.name],
)

<button onClick={() => handleSendMessage(quickActions.practice.prompt)}>
  {quickActions.practice.label}
</button>
```

课程为空或课程列表尚未加载时，派生函数必须返回不带具体学科假设的通用回退；发送动作仍应走同一个
`useWorkspaceChat.sendMessage`，以保留当前课程归属和资料隔离语义。

---

## Server State

<!-- How server data is cached and synchronized -->

调用后端 API、SSE 和附件列表的状态放在 `useWorkspaceChat` 内，通过返回值下发。所有执行入口
必须走同一个 `sendMessage` 或明确的统一运行函数，不得在组件中使用本地 `setTimeout` 模拟成功。

---

## Common Mistakes

<!-- State management mistakes your team has made -->

### Common Mistakes

- **错误**：右侧按钮直接启动本地 loading，同时中间区再发送一次消息。
  **正确**：右侧只构造参数并调用统一执行入口；loading 由 `isAiTyping/runStatus` 单一来源驱动。
- **错误**：右侧复制完整 `ArtifactCard`，导致一个成果出现两份详情。
  **正确**：右侧显示标题、类型、状态和“详情在中间对话区展示”，完整内容只在中间区展示。
- **错误**：新对话初始化时把工作台资料误当作当前会话附件，或为此创建空 conversation。
  **正确**：保留 `workspaceAttachments`；课程任务发送时将课程资料作为上下文，只有对话级上传才更新
  `conversationAttachments`。
- **错误**：只依赖前端资料列表加载完成后才把课程资料 ID 发给后端。
  **正确**：前端发送当前已知的课程资料 ID，后端对课程任务的空列表再做一次课程范围兜底。

### Course agent history aggregation

- `agentHistory` is loaded and refreshed by `useWorkspaceChat`; the right panel must not fetch course history or keep a
  second copy of run state.
- `route.agentId` is the single source for automatic group switching after `route_decision`/SSE. Opening a historical
  task restores the latest assistant `agent_id` into the same route state.
- The aggregation panel displays run metadata and short summaries only. It opens the owning conversation for full
  messages and Artifact details instead of duplicating `ArtifactCard`.

### Course resource isolation

- `useWorkspaceChat` is the single owner of the course-visible attachment projection. For a course task, an attachment
  is visible only when `attachment.course_id === courseId` or `attachment.course_id === null` (shared material).
- Course resource views must render this projection and must not contain hard-coded demo filenames or files from another
  course. A course switch must clear the previous attachment state before the new `GET /workspaces/current/attachments?course_id=...`
  response is applied.
- Course task requests must derive `selected_attachment_ids` from the same filtered projection, so stale UI state cannot
  leak another course's material into an agent run.

**Wrong**:

```tsx
const cards = ['匿名学情表.xlsx', 'Python高级函数教案.docx']
return <ResourceGrid files={cards} />
```

**Correct**:

```tsx
const attachments = mergeAttachments(conversationAttachments, workspaceAttachments)
  .filter((item) => item.course_id === courseId || item.course_id === null)
```
