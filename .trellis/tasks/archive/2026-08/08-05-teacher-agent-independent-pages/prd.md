# 教师 Agent 独立首页与详情页改造

## Goal

将教师工作台中的“课堂互动”和“课程迭代”独立智能体改造成与“学情分析”一致的页面式工作流：进入智能体先看到首页和历史记录，选择记录后进入独立详情页，详情页支持返回首页，不再通过历史弹窗承载结果。

## Background and Confirmed Facts

- 学情分析已经在 `apps/web/src/components/TeacherWorkspace.tsx:1720-1826` 具备独立页面层、首页历史记录、历史会话恢复、结果页返回首页和重新分析入口。
- 课堂互动和课程迭代仍通过 `TeacherAgentPreparationPanel` 创建独立任务；当前非学情分析智能体点击左侧入口会直接进入准备页。
- `TeacherAgentHistoryPanel` 目前以右侧响应式历史聚合面板展示课程级智能体记录，`HistoryDetailModal` 在 `TeacherWorkspace.tsx:1882-2030` 中以对话框展示非学情分析成果。
- `useWorkspaceChat` 已能通过 `conversations` 列表筛选无课程独立任务，并通过 `openConversation` 恢复消息、附件和 artifact；不需要新增 API 或 artifact schema。
- 课堂互动对应 `classroom_activity_package`、`classroom_observation`、`classroom_summary`；课程迭代对应 `course_iteration`、`lesson_design`、`lesson_plan`、`question_set`、`quiz` 等成果类型。
- 本次改动只聚焦教师工作台前端展示和导航状态，保留现有生成任务、SSE、会话恢复、课程工作流和后端契约。
- 本次只新增/改造 `course_id = null` 的课堂互动和课程迭代独立智能体；课程级智能体、课程历史聚合面板、课程任务对话和现有历史详情弹窗不做行为改动。
- 当前实现存在三个已复现缺陷：打开独立历史和新任务启动后错误地保留首页状态；通用“任务”列表只排除了独立学情分析；流式请求取消后可能留下 `running` 运行状态并阻止再次新建。
- 两次真实课程迭代运行均为 `completed` 且已有助手文本，但普通请求经 `GenericChatExecutor` 返回时没有 Artifact；课件分支生成的 `slide_deck` 又被独立详情页的类型过滤排除。

## Requirements

- 课堂互动和课程迭代的独立入口都显示统一的首页：智能体标题、简介、新建任务入口以及该智能体的历史记录。
- 两个独立智能体首页顶部沿用本次学情分析调整：不显示“教师 Agent · 独立分析/独立任务”等副标题，不显示标题左侧 Logo，首页标题使用“课堂互动”和“课程迭代”。
- 两个独立智能体的准备页也沿用同一视觉约束，去掉“教师 Agent · 独立任务”副标题和标题左侧 Logo，但保留现有表单字段、文件选择和提交行为。
- 首页历史记录只展示属于当前智能体的记录；点击记录后进入页面级独立详情页，不渲染通用任务消息、输入框或历史弹窗。
- 独立详情页展示当前历史记录的摘要和 artifact 内容，提供复制、导出等已有成果操作，并提供明确的“返回首页”操作。
- 从详情页返回后保留对应智能体首页；点击“重新开始/新建任务”才进入现有准备流程，提交成功后进入新的独立详情页。
- 历史记录恢复必须以当前会话和当前智能体为边界，切换到其他智能体、新建任务或退出页面时不得残留上一个详情结果。
- 点击独立历史、或独立任务开始执行后，必须立即进入该智能体的详情/执行页，不得继续停留在首页。
- 所有无课程的独立教师 Agent 记录只出现在对应 Agent 首页，不得出现在左侧通用“任务”/对话列表；底层会话仍可作为运行和成果归属载体。
- 流式请求被浏览器导航、热更新或主动停止取消时，关联运行必须从 `running` 收口为可重试的失败状态，不能永久锁住“新建任务”。
- 普通独立课程迭代成功后必须创建 `course_iteration` Markdown Artifact；请求课件/PPT 时继续创建 `slide_deck` Artifact。
- 独立课程迭代详情必须展示 `course_iteration` 和 `slide_deck` 两类成果；`slide_deck` 复用现有幻灯预览并支持 PPTX/Markdown 导出。
- 修复前已经完成但只有助手消息、没有 Artifact 的独立历史记录，仍必须以“历史文本成果”展示和复制；不迁移或伪造旧 Artifact。
- 课堂互动和课程迭代的独立详情页使用页面布局，不使用 `HistoryDetailModal` 对话框；课程级历史记录仍使用原有 `HistoryDetailModal`，其他未纳入本次改造的智能体维持现有行为。
- 保持桌面和窄屏布局、reduced-motion 行为、单一滚动容器以及现有教师工作台功能不变。

## Acceptance Criteria

- [ ] 点击“课堂互动”进入首页，首页包含新建任务入口和课堂互动历史记录；点击新建任务后进入现有准备页。
- [ ] 点击“课程迭代”进入首页，首页包含新建任务入口和课程迭代历史记录；点击新建任务后进入现有准备页。
- [ ] 两个首页和对应详情页都不显示顶部“教师 Agent · 独立分析/独立任务”副标题或标题左侧 Logo。
- [ ] 点击课堂互动或课程迭代历史记录后，详情在独立页面中打开而非对话框；页面可展示对应摘要/artifact，并可返回首页。
- [ ] 从历史详情返回首页、切换智能体、关闭工作台、新建任务后，不会继续展示旧详情或旧 artifact。
- [ ] 课堂互动历史点击后离开首页并打开所选记录；新建任务提交后进入执行/详情页，而不是只新增一条通用对话。
- [ ] 学情分析、课堂互动、课程迭代等无课程独立 Agent 均不显示在左侧通用“任务”/对话列表，只显示在各自首页历史中。
- [ ] 流式执行取消后运行状态不再停留在 `running`，用户可以重新进入准备页并再次执行。
- [ ] 普通课程迭代的完成事件关联 `course_iteration` Artifact，历史恢复后可查看、复制和导出 Markdown。
- [ ] 包含课件/PPT意图的课程迭代关联 `slide_deck` Artifact，独立详情页可预览并导出 PPTX/Markdown。
- [ ] 修复前两条无 Artifact 的课程迭代历史点击后可查看完整助手文本，不再显示“本次任务没有生成成果”。
- [ ] 现有学情分析独立首页/详情、课程级任务、智能体历史聚合面板和未纳入范围的历史详情行为不回归。
- [ ] `npm.cmd run lint`、`npm.cmd run build`、`git diff --check` 通过。

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
