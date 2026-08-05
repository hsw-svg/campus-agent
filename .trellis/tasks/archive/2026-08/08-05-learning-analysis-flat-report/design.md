# 技术设计：学情分析结果页面平铺展示

## 现状与根因

`TeacherWorkspace` 当前根据 `isLearningAnalysisArtifactMessage` 在助手消息气泡内部渲染 `LearningAnalysisReport`。报告虽然使用了真实 artifact，但它被消息列表的气泡布局包裹；页面的 `stage` 只是本地展示状态，关闭准备层或重新进入时会被清空。`useWorkspaceChat.openConversation` 会先清空本地资源，再从会话消息中的 artifact 引用恢复 artifact，因此恢复来源已经存在，缺少的是稳定的页面级渲染入口。

## 数据流

1. `useWorkspaceChat` 继续负责创建/流式更新会话、保存 artifact，以及通过 `openConversation` 按消息引用恢复 artifact。
2. `TeacherWorkspace` 从当前独立会话的 `artifacts` 中选择最新的 `type === 'learning_analysis'` artifact，并额外以当前会话 ID作为边界。
3. 当 `activeStandaloneAgentId === 'learning_analysis'` 时，工作台切换为独立学情分析结果层，任务消息、任务输入和历史管理全部被遮罩并设为 inert；结果层只读取上述 artifact。
4. 点击学情分析入口时，如果已有最近的无课程 `learning_analysis` 会话，则通过 `openConversation` 在后台恢复 artifact 并直接打开结果层；没有历史会话才打开上传准备页。
5. `clearChat` 只清空当前运行态，服务端会话仍可由入口重新恢复；“重新分析”明确清空当前运行态并再次打开准备页。报告首次生成或恢复后只自动聚焦一次报告顶部，同一报告不会重复抢夺滚动位置。
6. 独立结果页的报告卡片通过左上角返回按钮切换到学情分析首页；首页读取无课程 `learning_analysis` 会话列表展示历史记录，并提供上传新文件入口。

## 渲染结构

独立学情分析使用覆盖右侧工作区的专属页面层；通用课程任务仍保留原工作台布局：

```text
学情分析专属层
├─ 固定关闭按钮
├─ 学情分析标题与状态
├─ 页面级 LearningAnalysisReport（有 artifact 时）
└─ 复制 / 重新分析
```

报告区使用独立的语义标题/区域和 `w-full`，复用现有 `LearningAnalysisReport` 的报告内容，但不传入跨任务生成回调。报告外层和内部数据卡片不使用明显硬边框，改用背景色、留白和轻微阴影保持层次。独立层不渲染任何通用聊天消息，因此不会出现任务对话管理或气泡报告。

## 恢复与边界

- 当前 artifact 选择器使用 `artifacts` 中反向查找，并要求 `artifact.conversation_id === activeConversationId`；没有活动会话时返回 `null`。
- `openConversation` 的异步清空阶段不会导致旧报告闪回：渲染条件同时依赖活动会话 ID和匹配 artifact。
- 切换课程、切换独立智能体或调用 `clearChat` 后当前运行态报告立即卸载；再次点击学情分析入口时从最近独立会话恢复，而不是展示通用任务列表。
- 历史详情弹窗继续复用 `LearningAnalysisReport`，不改变其导出/复制行为；本任务只改变工作台主页面的展示位置。

## 动效与响应式

- 页面级报告使用现有 Motion 淡入/位移动画，动画参数读取 `shouldReduceMotion`；reduced-motion 下仅保留短淡入。
- 报告沿用组件内部的响应式网格，外层不再增加嵌套滚动；主工作台滚动容器保持唯一滚动 owner。
- 报告区和消息区之间使用稳定间距，切换 artifact 时不改变右侧历史面板宽度，也不触发顶部课程内容闪烁。

## 非目标

- 不改后端 artifact 生成、API schema、数据库迁移或历史面板的聚合逻辑。
- 不重新设计报告图表，也不把课堂互动、课程迭代的其他 artifact 改成页面级展示。
