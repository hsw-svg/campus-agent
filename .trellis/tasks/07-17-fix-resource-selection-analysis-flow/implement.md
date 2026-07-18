# 实施计划

## Ordered Checklist

1. [x] 抽取/复用附件响应和上传处理逻辑，新增工作区级读取、上传端点，并保持工作区权限过滤。
2. [x] 扩展 `api.ts` 类型和请求函数，区分工作区资料与会话附件。
3. [x] 重构 `useWorkspaceChat`：加载工作区资料、按会话加载附件、清理时保留工作区资料、上传时按 scope 选择端点。
4. [x] 更新 `ResourcePicker`、`ClassroomInteractionPanel` 和教师工作台 props，准确显示两个资料来源。
5. [x] 将教师“分析学情”快捷按钮接入选中资料检查和真实 `sendMessage`，移除该入口对 `startAnalysis` 演示流程的依赖。
6. [x] 增加后端附件接口/仓储回归测试和前端静态/浏览器冒烟验证。
7. [x] 将课程、对话、AgentRun、Artifact 的组织原则写入设计、开发和前端文档。
8. [x] 右侧课堂互动面板改为成果索引，完整 Artifact 只在中间对话区展示。
9. [x] 增加统一 \`RunRequest\` 和同意图运行中的前端去重。
10. [x] 引入轻量 \`CourseContext\` 与教学闭环的父子 Run/Artifact 引用。
11. [x] 将 Conversation 产品化为任务，新增课程容器、独立任务和课程资料隔离。
12. [x] 根据最新需求移除教师右侧资料选择区，课程任务默认使用全部课程可见资料，并增加空附件 ID 的后端兜底。

## Validation

- `cd apps/web; npm.cmd run lint`
- `cd apps/web; npm.cmd run build`
- `cd apps/api; ..\\..\\.venv\\Scripts\\python.exe -m pytest`
- 浏览器：角色进入 → 课程资料可见 → 新建任务仍可用 → 分析学情 → 验证真实任务状态/结果；同时确认右侧不再出现资料选择区。
- 交互回归：右侧点击生成活动包时，中间区和右侧区只显示同一个运行状态；活动包完整内容只出现一个详细展示位置。

## Risky Files / Rollback Points

- `apps/api/app/api/attachments.py`、`apps/api/app/api/workspaces.py`：接口和上传流程；先运行后端测试。
- `apps/web/src/hooks/useWorkspaceChat.ts`：状态生命周期；重点检查切换会话、创建会话和上传竞态。
- `apps/web/src/components/TeacherWorkspace.tsx`：旧演示入口和真实工作台并存；避免误删课堂互动 P0 UI。

每个阶段保持小范围 diff；若 API 变更导致前端无法启动，先回退 API 路由改动，再单独落地前端状态拆分。
