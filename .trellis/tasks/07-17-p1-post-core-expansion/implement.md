# P1 扩展能力执行计划

## 0. 规划审阅与基线

- [x] 审阅父任务 PRD、设计、子任务 PRD 和本清单；确认第一切片范围。
- [x] 记录 `git status --short`，保留现有 `AGENT.md` 删除、`AGENTS.md` 修改和 `CLAUDE.md` 修改，不将其误当成实现变更。
- [x] 建立验证基线：后端与前端命令已执行并记录结果。
- [x] 仅在规划审阅后启动第一个子任务，不启动父任务直接写业务代码。

## 1. 后端子任务：学生与行政 Executor

- [x] 为 `course_qa`、`personal_tutor`、`meeting_minutes`、`todo_breakdown` 增加独立 AgentSpec 配置、prompt、输入契约和 ContextPolicy。
- [x] 增加 Pydantic 结构化输出模型和公共 JSON 解析/Markdown 生成辅助代码；无效 JSON 使用稳定错误，不做隐式修复。
- [x] 实现四个角色 Executor，接入 `AgentExecutorRegistry`，为每个结果生成单一结构化 Artifact 和有限引用。
- [x] 校验学生资料、行政资料和 selected Artifact 的 workspace/conversation 边界；保持学情明细过滤。
- [x] 增加无真实 Key 的 Executor 单测、缺失输入/无效结构化输出测试、AgentRun/SSE API 测试、跨角色/跨工作区拒绝测试。
- [x] 运行后端全量 pytest；记录环境依赖导致的失败，不以跳过业务测试代替通过。

## 2. 前端子任务：Context、Artifact 与 React 工作区

- [x] 在实际 React 组件中接入工作区附件、当前会话附件、当前任务附件和 Artifact 的分组选择。
- [x] 确认 `streamMessage` 只提交显式选中的 ids；切换角色/会话/新建对话时清空选择。
- [x] 扩展 `ArtifactCard` 和学生/行政工作区，展示四种 P1 结构化结果、真实引用、复制、Markdown/CSV 导出。
- [x] 补齐 `needs_input`、`failed`、`retry`、`degraded`、SSE 中断和导出失败的可操作中文提示。
- [x] 保持教师 P0 组件可用，移除/不扩展与 API 真实结果冲突的静态演示替代路径。
- [x] 在 `apps/web` 运行 `npm.cmd run lint` 和 `npm.cmd run build`；浏览器/演示冒烟检查已尝试，但当前环境无可用浏览器运行器且 Vite 未稳定监听，已记录为环境后续项。

浏览器运行器在当前环境不可用，已记录于前端子任务；`npm.cmd run lint` 与 `npm.cmd run build` 均通过。

## 3. 文档子任务：代码事实对齐

- [x] 全局搜索受影响文档中的旧前端栈描述，确认没有残留旧技术栈主张。
- [x] 根据 `apps/web/package.json`、`vite.config.ts`、`src/` 和 Docker 配置，将文档改为 React 19、Vite、TypeScript、Tailwind CSS、3000 开发端口、8080 Docker 入口和实际 lint/build 命令。
- [x] 更新架构图、目录示例、状态管理和组件命名；只标记已经实现的 P1 能力。
- [x] 同步 `AGENTS.md` 项目规范及 UI 提示文档，保留明确的产品边界和安全约束。
- [x] 运行 `git diff --check`、关键文档搜索和必要的 Markdown 结构检查。

## 4. 集成验证与交付

- [x] 运行后端全量测试、前端 lint/build 和 Docker Compose build。
- [x] 通过 API/Executor 回归覆盖固定演示路径：学生资料选择 → CourseQA、错题/作业 → PersonalTutor、行政输入/材料 → MeetingMinutes/TodoBreakdown → CSV 导出；浏览器端冒烟待可用运行器补做。
- [x] 验证教师资料在学生/行政空间不可见，未选择资源不进入请求上下文，来源只显示当前 Executor 实际使用资料。
- [x] 使用 `trellis-check` 规范完成最终质量检查；当前模板 spec 无需更新。
- [ ] 完成后整理单一主题提交；提交前向用户报告验证结果并确认是否提交，遵守项目不自动提交规则。

## 依赖与回滚点

- 后端契约稳定后再启动前端子任务；前端不能自行猜测结构化字段。
- 文档子任务在代码和验证稳定后执行，避免文档先于实现声称完成。
- 若结构化输出或隔离测试失败，先回滚对应 Executor/ContextPolicy 变更，不回滚用户已有的 Agent 指令文件整理。
