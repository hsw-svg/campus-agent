# P1 核心闭环后的扩展能力

## Goal

在教师 P0 教学闭环已经具备 AgentSpec、Executor、ContextPolicy、结构化校验、Artifact 和 SSE/AgentRun 基础后，补齐学生与行政岗位的可演示扩展能力，并让教师 P1 能力遵守明确资料选择和可追踪成果约束。

## Confirmed Facts

- `apps/api/app/agents/registry.py` 已声明学生、教师和行政的 P1 agent id，但 `AgentExecutorRegistry` 目前只为 `learning_analysis`、`lesson_design` 和 `classroom_interaction` 提供独立 Executor，其余会回落到 `GenericChatExecutor`。
- `AgentSpec`、`AgentRequest`、`ContextBuilder`、`selected_attachment_ids`、`selected_artifact_ids`、AgentRun 状态和 SSE 已有基础实现，但 P1 agent 尚未声明细化的输入契约、资料策略和结构化输出校验。
- Artifact 已支持工作区隔离、会话内选择、列表/读取和 Markdown/CSV 基础导出；需要统一各 P1 结果的数据契约和导出内容。
- 前端已经有角色工作区、统一聊天 Hook、附件/成果 API 和基础导出 API，但学生/行政 P1 的选择器、结构化结果展示、当前任务实际资料反馈和错误恢复仍不完整。
- `docs/开发文档.md` 将以下列为 P1：作业批改、课程迭代、学生课程资料问答、学生错题答疑、行政会议纪要和待办、教学报告和更多导出格式。
- P1 智能体必须满足：注册 AgentSpec、独立 Executor、输入契约、ContextPolicy、确定性数据由程序计算、结构化输出校验、可追踪且隔离的引用来源，以及成功/输入不足/异常/隔离测试和统一 AgentRun/SSE 执行路径。

## Requirements

1. 每个纳入本任务的 P1 agent 必须拥有独立 AgentSpec、输入契约、ContextPolicy 和 Executor；可以复用通用模型调用基础设施，但不能只注册名称。
2. 教师课程迭代和教学报告只能读取用户在当前任务中明确选择的允许资料或 Artifact，不得隐式扫描工作区或合并未选择成果。
3. 学生课程问答只能读取当前学生工作空间明确选择的课程资料；学生错题答疑只能读取当前学生空间明确选择的错题、作业和自述薄弱点，不得访问教师/行政空间或教师学情明细。
4. 行政会议纪要和待办拆解只能读取当前行政工作空间明确选择的材料；会议纪要至少输出议题、决议、负责人和待办，待办支持 Markdown 与 CSV；不得增加系统内通知发布或跨角色推送。
5. 所有结构化结果必须经程序校验；输入不足、模型失败、无效部分结果和降级状态通过 AgentRun/SSE/Artifact 统一表达，部分合法结果应按文档要求保留并报告丢弃原因。
6. Artifact 导出格式和来源字段保持统一，前端明确区分工作区资料库、当前会话附件和当前任务实际使用的附件/Artifact，并能展示当前 Executor 的真实引用来源。
7. 新增后端单元/API/隔离测试；前端按当前仓库已有能力执行 TypeScript 检查、生产构建和浏览器/演示冒烟，覆盖成功、输入不足、异常、重试、导出和跨角色/跨工作区拒绝，不为本轮无测试基础的前端包强行引入新的测试框架。
8. 以仓库当前实现为技术栈事实来源；发现开发文档、设计文档、前端文档或项目规范与代码冲突时，同步修正文档。例如 `apps/web` 当前是 React 19 + Vite + TypeScript + Tailwind CSS，并以现有 TypeScript 检查和构建脚本为验证依据，不按文档中的 Vue/Pinia/Element Plus 方案新增代码。

## Acceptance Criteria

- [ ] 规划阶段明确父任务下的独立交付切片、边界、依赖和验证命令。
- [ ] 每个已交付 P1 agent 可通过统一 AgentRun/SSE 路径执行，并具备独立契约、ContextPolicy、Executor、结构化校验和来源追踪。
- [ ] P1 agent 不会读取未选择的附件/Artifact、其他角色空间或教师学情行级数据。
- [ ] 学生和行政结果能在前端以可读结构化内容展示，并支持规定的复制/Markdown/CSV 导出；错误和输入不足有可操作提示。
- [ ] 后端与前端相关验证通过（后端 pytest、前端 `npm run lint`/`npm run build` 及可执行的浏览器冒烟），Docker Compose 构建和项目既有回归测试不受破坏。
- [ ] `docs/开发文档.md`、`docs/设计方案.md`、`docs/前端开发文档.md` 及受影响项目规范准确描述当前 React 前端技术栈、端口、测试和目录约定。

## Out of Scope

- 账号、登录、JWT、班级、选课、师生关系、跨角色推送和通知发布。
- 在线课堂扫码答题、实时学生端互动、学生反馈回流、语音口语练习和复杂课件导出。
- 将 LangChain/LangGraph 引入公共 AgentSpec 或业务状态模型。

## Agreed Scope

本轮先交付“学生 CourseQA + PersonalTutor、行政 MeetingMinutes + TodoBreakdown、共享 Context/Artifact 导出与前端资料展示”这一垂直切片，再按相同契约扩展教师 grading/course_iteration/teaching_report。这样先验证多角色隔离和统一执行链，控制本轮回归面；后续教师 P1 留在父任务的后续子任务中。
