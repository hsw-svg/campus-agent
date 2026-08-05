# 技术设计：课程切换驱动教师端快捷任务

## 1. 边界

本次改动限定在 `apps/web/src/components/TeacherWorkspace.tsx`。课程选择、对话清理和消息发送已经具备正确的 `courseId` 传递链路，不改动 `apps/web/src/api.ts`、`useWorkspaceChat` 或后端接口。

## 2. 数据流

```text
courses + activeCourseId
        ↓
activeCourse / activeCourseName
        ↓
buildTeacherQuickActions(activeCourseName)
        ↓
欢迎区、报告操作区、输入框上方标签
        ↓
handleSendMessage(action.prompt)
        ↓
useWorkspaceChat.sendMessage(courseContext)
        ↓
按当前 courseId 创建或继续任务
```

课程切换时，已有 `activeCourseId` 状态更新；`activeCourse` 和快捷任务的派生值随之重新计算。现有课程切换逻辑会清空未完成对话，避免新快捷任务继续使用旧对话上下文。

## 3. 快捷任务模型

在教师工作区组件内定义本地的 `TeacherQuickAction` 结构，至少包含：

- `id`：`practice`、`interaction`、`diagnosis`。
- `label`：用于标签或按钮显示的动态文案。
- `prompt`：用于发送给现有对话流程的动态提示词。

快捷任务工厂接收当前课程名称。选中课程时，将课程名称放入显示文案和提示词；未选中课程时返回通用版本。图标和卡片布局继续由现有 JSX 控制，避免为了动态文本引入图标组件类型或新组件。

## 4. 入口复用

- 欢迎区使用 `practice` 和 `interaction`。
- 学情报告后的主操作使用 `practice`。
- 输入框上方标签使用完整的三项快捷任务。

所有入口只读取快捷任务定义中的 `label` 和 `prompt`，不再内联重复字符串。

## 5. 兼容与取舍

- 课程列表目前可直接提供稳定的课程名称，因此不额外请求课程详情，避免切换课程时增加加载状态和网络竞态。
- 首版不把课程描述拼进标签，避免课程描述过长导致快捷标签难以阅读；对话请求仍会通过现有 `courseContext` 传递当前课程 ID 和名称。
- 快捷任务只在当前课程发生变化时通过 React 派生状态更新，不需要缓存或随机刷新。
- 课程名称过长时，标签沿用现有横向滚动布局，并为按钮保留 `title` 以便查看完整文案。

## 6. 回退与风险

如果课程列表尚未加载或用户切换到“不关联课程”，快捷任务退回通用文案，且不出现 Python 等学科假设。风险主要是遗漏重复入口；通过搜索原固定文案和 lint/build 验证覆盖。
