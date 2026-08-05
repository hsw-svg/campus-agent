# 实施计划：课堂互动与课程迭代独立页面

## 实施步骤

1. 读取并核对前端 Trellis 规范，锁定 `TeacherWorkspace`、`TeacherAgentPreparationPanel` 和现有独立学情分析页面的代码边界。
2. 将独立智能体的首页/准备页/详情页状态抽象为可复用判断，保留学情分析现有行为，并为课堂互动、课程迭代增加无课程历史筛选和会话恢复。
3. 为课堂互动和课程迭代增加页面式首页：标题、简介、新建任务入口、历史记录及空状态；历史项显示标题和时间，不进入课程级历史面板。
4. 为两个智能体增加独立详情页：恢复当前会话后展示摘要与相关 artifact，提供返回首页、复制和导出；确保不再调用 `HistoryDetailModal`。
5. 调整独立准备页顶部文案和标识，保留现有字段、校验、文件上传和任务提交；检查课程级调用路径未改变。
6. 静态检查状态边界：切换智能体、关闭页面、返回首页、重新开始、新建任务、历史恢复和空历史状态均不残留旧 artifact。
7. 修正历史点击和任务启动后的首页/详情状态；统一从通用任务列表排除所有无课程独立 Agent 会话。
8. 为流取消补充后端回归测试，确保 AgentRun 从 `running` 收口为 `failed/stream_cancelled`，并验证用户可重新执行。
9. 先扩展独立课程迭代 API 回归，要求普通请求产生 `course_iteration` Artifact；再修改执行器包装通用文本结果。
10. 将 `slide_deck` 纳入独立课程迭代成果类型，并在详情页按类型复用 `SlideDeckPreview` 与对应导出操作。

## 验证命令

在 `apps/web` 执行：

```powershell
npm.cmd run lint
npm.cmd run build
```

在仓库根目录执行：

```powershell
git diff --check
```

运行教师独立 Agent 后端回归：

```powershell
cd apps/api
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_teacher_standalone_agents.py
```

同时用 `rg` 检查：

- 独立课堂互动/课程迭代历史只匹配 `course_id === null`。
- 独立页面详情分支不渲染通用聊天输入、课程历史面板或 `HistoryDetailModal`。
- 课程级 `TeacherAgentHistoryPanel`、`ClassroomInteractionPanel` 和历史弹窗调用仍存在且 props/回调未被改写。

## 风险文件与回滚点

- `apps/web/src/components/TeacherWorkspace.tsx`：状态机、页面覆盖层和历史恢复主改动；优先以小范围补丁修改，避免重排课程工作台。
- `apps/web/src/components/TeacherAgentPreparationPanel.tsx`：仅调整独立准备页头部视觉；不修改提交 payload。
- `apps/web/src/components/TeacherAgentHistoryPanel.tsx`：默认不修改，作为课程级行为保护边界。
- `apps/web/src/hooks/useWorkspaceChat.ts`：默认不修改，复用现有会话恢复；如确需调整，只允许修复独立会话恢复的边界并补充静态验证。

## 开始实现前检查

- [x] 用户已确认只改无课程独立智能体，课程级智能体功能不动。
- [x] `prd.md`、`design.md`、`implement.md` 已完成并通过用户审核。
- [x] 已读取前端 spec、共享 thinking guide 和 `DESIGN.md`。
- [x] 已记录当前工作区已有未提交修改，不覆盖或清理它们。
