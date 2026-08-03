# 技术设计：学生端交互式书本与学习空间

## 1. 方案边界

本任务只扩展学生端体验和现有 DeepTutor 浏览器边界，不新增数据库表、不引入新的状态管理库，也不改变 DeepTutor Server 的安装和进程编排。浏览器仍只请求当前 FastAPI 的 `/api/deeptutor/*`，FastAPI 再通过 HTTP/WebSocket 调用 `127.0.0.1:8001`。

## 2. 页面与状态模型

`StudentWorkspace` 保持现有工作台壳层，增加两个学生导航区：

- `学习空间`：`DeepTutorLearningSpacePanel`，负责概览、继续学习、统计、书本入口和知识库摘要。
- `交互教材`：`DeepTutorBookPanel`，负责书架、阅读器、目录、页面进度、本地笔记和页面问答。

两者不共享一份 React 全局状态。书本/页面/Socket 状态留在书本面板；学习空间读取同一个轻量 `useDeepTutorStudyState` 的本地学习记录，并在打开书本时回到书本面板。现有 `useWorkspaceChat` 仍只负责普通学习中心聊天，不被 DeepTutor 页面问答复制或改造。

### 本地学习状态

`src/hooks/useDeepTutorStudyState.ts` 定义并持久化：

```ts
interface DeepTutorStudyState {
  completedPages: Record<string, string[]>
  notes: Record<string, string>
  savedQuestions: SavedDeepTutorQuestion[]
  lastOpened: { bookId: string; pageId: string } | null
}
```

存储 key 使用 `campus-agent:deeptutor-study:<token 后 12 位>`，不把完整 token 写入 localStorage。所有读取经过 hook 的解析与默认值修复，损坏的 JSON 自动回退为空状态。状态只服务竞赛演示，不替代真实用户数据存储。

## 3. API 与数据流

```text
DeepTutor JSON/WS
  -> FastAPI /api/deeptutor
  -> src/api.ts 归一化（book / spine / page / block / chat event）
  -> DeepTutorBookPanel 书架/目录/页面/问答
  -> useDeepTutorStudyState 本地进度与记录
  -> DeepTutorLearningSpacePanel 概览投影
```

扩展 `src/api.ts` 的 DeepTutor 类型和归一化函数：

- `DeepTutorBook` 补充状态、章节数、页面数等可选统计字段。
- `DeepTutorPage` 补充统一的 `blocks`，从上游可能出现的 `blocks`/数组内容中提取 `id/type/title/content`。
- 兼容 DeepTutor 当前真实响应 envelope：spine 在 `{ spine: { chapters: [...] } }` 中返回、页面在 `{ page: {...} }` 中返回，区块正文通常位于 `block.payload`；归一化层会把章节下的 `page_ids` 展开为可阅读目录。
- 页面组件只消费归一化后的字段，不在 JSX 内读取 `raw.blocks` 或对 `unknown` 做散落类型断言。

问答继续使用 `getDeepTutorChatWebSocketUrl()` 和 `parseDeepTutorChatEvent()`。发送消息时附带 `book_id`、`page_id`、`session_id`、`kb_name`、`enable_rag`；收到文本事件时只追加当前 assistant 占位消息，`error`、`done`、`complete` 和关闭事件分别更新 UI 状态。

## 4. 组件职责

### `DeepTutorLearningSpacePanel`

- 首次进入并行加载书本和知识库，拥有加载、空态、错误态。
- 渲染欢迎区、四项统计、继续学习卡、书架摘要、知识库摘要和学习记录。
- 通过 `onOpenBooks(bookId?)` 回调打开书本面板；不直接加载页面正文或创建 WebSocket。

### `DeepTutorBookPanel`

- 书架：搜索、选中书本、统计卡和创建书本表单。
- 阅读器：目录侧栏、当前页、页面 block 卡、进度条、上一页/下一页、完成按钮、笔记编辑。
- 问答：页面上下文、流式消息、保存问题、断开清理。
- 在切换 book/page 时重置不应跨页面继承的问答和加载状态，并记录 `lastOpened`。

### `StudentWorkspace`

- 只做导航、面板挂载和内容宽度切换。
- 不保存 DeepTutor 的书本列表、页面内容、问答消息或进度，避免工作台壳层成为第二个状态源。

## 5. UI 约定

- 使用当前系统的 `bg-background`、`bg-surface`、`bg-secondary`、`text-on-surface`、`text-on-surface-variant`、`border-outline-variant` 等 token。
- 复用 lucide-react 图标、圆角卡片、紧凑字体和现有响应式断点；不引入上游的 CSS 变量、shadcn 组件或字体。
- 桌面端采用“书架/目录 + 阅读内容 + 页面问答”的三列结构；小屏幕改为书本选择、阅读、问答纵向布局，移动底部导航可进入学习空间和交互教材。
- 页面 block 以当前系统卡片呈现：正文使用 Markdown，提示/重点/练习使用不同的浅色容器；未知 block 降级为普通文本，不阻塞整页。

## 6. 失败与回收

- DeepTutor 书本/知识库加载失败只在对应面板显示错误，课程学习中心继续可用。
- WebSocket 在组件卸载、切换书本/页面或发送新问题前关闭旧连接；所有事件处理器只更新仍然存在的当前连接。
- 无 token、无书本、无目录、无页面分别提供可理解空态，不调用依赖 token 的 API。
- API 归一化对 `unknown`、数组、对象、空字段采用安全默认值，避免演示数据形状变化导致白屏。
