# 工作区资料与学情分析流程设计

## Architecture

保留现有 `useWorkspaceChat` 作为资料和发送状态的唯一编排入口，但把目前混合的 `attachments` 拆为两个来源：

- `workspaceAttachments`：由工作区级 API 加载，随角色/token 生命周期存在，跨对话保留。
- `conversationAttachments`：由会话级 API 加载，随 `activeConversationId` 切换。
- `selectedAttachmentIds`：只保存用户明确勾选的 ID，发送时合并检查两个来源中的 ID。

组件层接收两个明确的数组，`ResourcePicker` 和 `ClassroomInteractionPanel` 继续负责展示和勾选，不在 React 中执行路由、统计或隐式资料推断。

## API Contract

新增工作区级端点：

- `GET /api/workspaces/current/attachments` → `AttachmentResponse[]`，只返回当前工作区 `scope=workspace` 的资料。
- `POST /api/workspaces/current/attachments` → `AttachmentResponse`，只创建工作区资料，不要求 `conversationId`。

现有 `GET/POST /api/conversations/{conversation_id}/attachments` 继续处理 `scope=conversation`，对已有调用保持兼容。工作区级上传复用现有对象存储、解析和 embedding 流程，存储键改为工作区维度，不需要数据库结构变化。

## State Flow

```text
角色/token 变化
  ├─ GET workspace attachments → workspaceAttachments
  └─ 无 active conversation → conversationAttachments=[]

打开历史会话
  ├─ GET conversation attachments
  ├─ GET conversation artifacts/messages
  └─ 重置 selectedAttachmentIds / selectedArtifactIds

新建对话
  ├─ 保留 workspaceAttachments
  ├─ 清空 conversationAttachments、成果和选择
  └─ 资料可直接勾选；首次发送时再创建 conversation
```

发送前，教师端学情分析入口检查选中的可用表格数量；通过后调用既有 `sendMessage('分析学情')`，由后端校验并通过 SSE 返回结果。旧 `startAnalysis()` 仅用于演示的本地阶段状态从真实入口移除。

## Compatibility and Trade-offs

- 后端保留会话级附件 API，避免影响学生、行政和历史调用。
- 新增工作区 API 比创建空对话来获得 ID 更符合数据模型，也避免会话列表出现无消息对话。
- UI 仍允许工作区资料被显式勾选，但不会默认发送，保持既有安全隔离要求。
- “当前对话附件”在新对话中为空是正确语义；空状态需要改成上下文明确的文案，而不是总体“暂无可选资料”。

## Rollback

若工作区级上传 API 出现问题，可暂时回退前端上传到现有会话级端点；读取和显示状态拆分仍可保留，不涉及迁移回滚。

## 第二阶段：单任务源与双视图

当前后端已经通过 \`AgentRun\` 和 SSE \`run_id\` 表达一次执行；本阶段不新增数据库字段，先收敛前端职责：

- 中间对话区是完整消息和 Artifact 的唯一详细展示位置。
- 右侧 \`ClassroomInteractionPanel\` 只负责参数、资料、运行摘要、成果选择和下一步操作。
- 右侧不再渲染完整 \`ArtifactCard\`，避免与中间区重复。
- 中间区和右侧区继续读取 \`useWorkspaceChat\` 的 \`isAiTyping\`、\`runStatus\`、\`toolStatus\` 和 \`route\`。
- 后续课程上下文和教学闭环以 \`course_id\`、\`workflow_id\`、\`input_refs\` 为扩展方向，暂不扩大本轮附件修复的后端数据模型。
