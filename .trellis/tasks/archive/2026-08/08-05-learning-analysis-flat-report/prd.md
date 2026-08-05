# 学情分析结果页面平铺展示

## Goal

将学情分析执行后的可视化报告从对话嵌入展示改为教师工作台页面直接平铺展示，并保证关闭和重新进入时状态可恢复。

## Requirements

- 学情分析是独立智能体。用户上传材料并执行后，直接留在“学情分析”专属页面展示结果，不进入通用任务对话工作台。
- 独立学情分析页面不显示任务消息、任务输入框、智能追问、课程归属、课程资料管理或智能体历史管理；只保留报告展示、必要的复制操作、关闭/返回和重新分析入口。
- 报告使用现有 `LearningAnalysisReport` 组件的指标、图表、薄弱点、诊断和策略内容，但不在独立页面提供“生成课程迭代方案”等跨任务动作。
- 学情分析报告及其内部数据卡片使用背景、留白和轻微层次感区分，不使用明显的硬边框。
- 分析结果卡片左上角提供“返回学情分析首页”按钮；首页展示历史分析记录，并提供上传新文件入口。
- 报告数据必须绑定当前独立学情分析会话的 `learning_analysis` artifact；切换课程、新建任务或进入其他智能体时，不得显示上一个结果。
- 关闭独立学情分析页面后再次点击“学情分析”入口，应自动恢复最近一次独立学情分析结果；点击“重新分析”才创建新的准备流程。没有历史结果时仍显示上传引导页。
- 报告的指标、图表、薄弱点、诊断、策略和操作区沿用对话中现有报告的视觉与交互，不在本任务中重做图表内容或后端契约。
- 页面在窄屏和宽屏下均保持可读，报告切换动画遵守项目的 reduced-motion 约定，不引入第二个滚动容器或布局抖动。

## Constraints

- 只修改教师工作台及其直接渲染逻辑；不新增账号、课程权限、后端 API 或 artifact schema。
- 不覆盖工作区内其他未提交改动；不改变现有教师 Agent 历史面板的单实例响应式修复。
- 优先复用 `useWorkspaceChat` 的会话恢复和现有 `LearningAnalysisReport`，避免为同一份 artifact 建立另一套状态。

## Acceptance Criteria

- [x] 上传可用匿名学情表并执行分析后，专属页面直接显示报告，页面中没有任务消息、输入框、追问或历史管理区域。
- [x] 学情分析 artifact 只在独立学情分析页面渲染一次；通用任务对话不会再渲染独立报告。
- [x] 关闭后再次点击“学情分析”入口可以恢复最近一次报告；点击“重新分析”可以回到上传准备页。
- [x] 结果卡片左上角返回按钮可以回到学情分析首页；首页可查看历史记录并启动新文件分析。
- [x] 切换到其他智能体、新建任务或没有分析结果时，不会残留旧报告。
- [x] 桌面和窄屏布局均通过 `npm.cmd run lint`、`npm.cmd run build` 与 `git diff --check`；不引入 TypeScript 错误。

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
