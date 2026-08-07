# 技术设计：学生端交互教材与学习记录优化

## 1. 边界与架构

本轮只改 `apps/web` 学生端。DeepTutor 继续由现有 FastAPI 同源代理提供书本、页面和 WebSocket；不新增 API 路由、数据库表或后端身份模型。`StudentWorkspace` 仍只负责导航和面板挂载，书本页面状态继续留在 `DeepTutorBookPanel`，跨菜单恢复所需的轻量状态集中到 `useDeepTutorStudyState`。

```text
DeepTutorBookPanel
  ├─ 书架 / 目录 / 页面阅读器 / 页面问答
  └─ useDeepTutorStudyState(token)
       ├─ completedPages
       ├─ notes + noteMeta
       ├─ savedQuestions
       ├─ chatHistory[bookId:pageId]
       ├─ chatSessions[bookId:pageId]
       └─ lastOpened
             │
             ▼
DeepTutorLearningSpacePanel
  └─ 最近笔记 / 待复习问题列表 → StudentWorkspace → 指定书本和页面
```

## 2. 本地状态与兼容

扩展 `DeepTutorStudyState`：

```ts
interface DeepTutorChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface DeepTutorStudyState {
  completedPages: Record<string, string[]>
  notes: Record<string, string>
  noteMeta: Record<string, { bookTitle?: string; pageTitle?: string; updatedAt: string }>
  savedQuestions: DeepTutorSavedQuestion[]
  chatHistory: Record<string, DeepTutorChatMessage[]>
  chatSessions: Record<string, string>
  lastOpened: { bookId: string; pageId: string } | null
}
```

- `readState` 对新增字段提供空默认值，并保留旧 `notes`、`savedQuestions`、`completedPages`、`lastOpened` 数据。
- 所有 key 使用现有 `bookId:pageId` 规则；chat history 限制为最近 30 条消息或合理字数上限，避免演示问答无限增长。
- `setPageNote` 同时写入笔记正文和可选页面标题；空笔记从列表中隐藏，但保留或删除的行为要保持简单可预期。
- `saveQuestion` 继续去重并限制数量；问答正文由 `setChatHistory` 保存，回答在流式完成前也可保存为当前草稿，退出时不会丢失已经收到的文本。

## 3. 阅读器布局

- `DeepTutorBookPanel` 的桌面端三列网格保持不变，但中间 `<main>` 使用 `min-h-0`、视口相关 `max-height` 和 `overflow-y-auto`，使阅读内容在中间列内部滚动；移动断点取消固定高度，保持页面自然滚动。
- 页面上方保留标题、进度和页码导航；在 `page.blocks` 存在时增加“本页结构”横向滚动条，每个按钮带 block id，点击使用 `scrollIntoView({ behavior: 'smooth', block: 'start' })` 定位。
- 块容器增加稳定 DOM id 和 `scroll-mt`；不引入 IntersectionObserver 也能提供明确定位，减少当前组件改造量。若后续需要高亮当前块，可在独立迭代中补齐。
- 桌面端页面标题和结构条在阅读器内部保持可见或紧凑；正文卡片继续复用当前颜色 token、Markdown 组件和内容块语义。

## 4. 问答恢复流程

1. 进入页面时从 `chatHistory[pageKey]` 初始化 `messages`，从 `chatSessions[pageKey]` 初始化 `sessionIdRef`。
2. 提交问题时先写入 user 消息和 assistant 空占位，再调用现有同源 WebSocket；同时写入 `savedQuestions`。
3. 收到 `session` 事件时写入 page key 对应 session id；收到合格文本时更新 assistant 内容并同步 chat history。
4. 收到 `done`、error、close 或组件卸载时关闭 socket，保持已收到的历史；只在用户点击“清空”时清除当前 page key 的历史和 session id。
5. 页面切换先关闭旧 socket，再加载目标页正文和目标页历史，禁止旧连接事件污染新页面。

## 5. 学习空间列表与导航

- `DeepTutorLearningSpacePanel` 使用同一 hook 读取最近非空笔记、保存问题和问答摘要；以最近更新时间倒序展示有限条目，避免把概览页变成无穷列表。
- `onOpenBooks` 扩展为可选 `bookId`、`pageId`；`StudentWorkspace` 保存 `deepTutorBookId` 和 `deepTutorPageId`，`DeepTutorBookPanel` 在目录加载后优先打开指定页面，否则沿用 `lastOpened`/第一页。
- 记录缺少标题时显示“交互教材 / 页面记录”等安全兜底；书本尚未出现在书架时保留记录但禁用跳转或显示提示。

## 6. 取舍、回滚与验证

- 采用浏览器本地持久化，因为当前项目没有真实学生身份和跨设备同步授权；如果需要跨设备，需要另立后端契约，不在本轮隐式扩张。
- 不复制上游 Next.js 页面、服务端 Notebook/Question Bank 管理、编辑器或复杂 block renderer；当前应用只做能验证学生阅读闭环的最小增强。
- 回滚点集中在 `StudentWorkspace.tsx`、`DeepTutorBookPanel.tsx`、`DeepTutorLearningSpacePanel.tsx`、`useDeepTutorStudyState.ts`，以及必要的 `src/api.ts` 类型，不修改 Docker/API 边界。
- 验证至少运行 `npm.cmd run lint`、`npm.cmd run build`，并用 `git diff --check` 检查；如新增可抽离的状态解析逻辑，再补最小单元测试或通过构建覆盖。
