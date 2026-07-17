# 实施计划

## Ordered Checklist

1. [x] 抽取/复用附件响应和上传处理逻辑，新增工作区级读取、上传端点，并保持工作区权限过滤。
2. [x] 扩展 `api.ts` 类型和请求函数，区分工作区资料与会话附件。
3. [x] 重构 `useWorkspaceChat`：加载工作区资料、按会话加载附件、清理时保留工作区资料、上传时按 scope 选择端点。
4. [x] 更新 `ResourcePicker`、`ClassroomInteractionPanel` 和教师工作台 props，准确显示两个资料来源。
5. [x] 将教师“分析学情”快捷按钮接入选中资料检查和真实 `sendMessage`，移除该入口对 `startAnalysis` 演示流程的依赖。
6. [x] 增加后端附件接口/仓储回归测试和前端静态/浏览器冒烟验证。

## Validation

- `cd apps/web; npm.cmd run lint`
- `cd apps/web; npm.cmd run build`
- `cd apps/api; ..\\..\\.venv\\Scripts\\python.exe -m pytest`
- 浏览器：角色进入 → 工作区资料可见 → 新建对话仍可见 → 勾选资料 → 分析学情 → 验证真实任务状态/结果；同时确认当前对话附件空状态文案。

## Risky Files / Rollback Points

- `apps/api/app/api/attachments.py`、`apps/api/app/api/workspaces.py`：接口和上传流程；先运行后端测试。
- `apps/web/src/hooks/useWorkspaceChat.ts`：状态生命周期；重点检查切换会话、创建会话和上传竞态。
- `apps/web/src/components/TeacherWorkspace.tsx`：旧演示入口和真实工作台并存；避免误删课堂互动 P0 UI。

每个阶段保持小范围 diff；若 API 变更导致前端无法启动，先回退 API 路由改动，再单独落地前端状态拆分。
