# 学生简历助手实施计划

## 1. 基线与规范

- [x] 使用 `trellis-before-dev` 读取本任务涉及的后端、附件、课程中心、跨层和前端规范。
- [x] 记录 `git status --short`，保留用户已有改动，不混入无关文件。
- [x] 运行简历助手将复用的附件、AgentRun、Artifact、课程中心和学生工作台基线测试/构建。

## 2. 数据与持久化

- [x] 新增 `StudentResumeProfile` 模型和 workspace-scoped repository/service。
- [x] 新增 `0014` Alembic 迁移，创建当前简历指针及必要索引/外键。
- [x] 在 Alembic metadata 与 `app.main.create_app` 模型注册中接入新模型。
- [x] 增加 profile 获取/替换测试，覆盖附件归属、scope、扩展名、解析状态和零文本。

## 3. 简历分析领域 API

- [x] 新增 `/api/resume-assistant/profile` GET/PUT 契约和稳定 `AppError`。
- [x] 新增课程证据快照构建逻辑，只接受当前工作区已开始且明确选择的课程。
- [x] 新增 `/api/resume-assistant/analyses/stream`，为每次分析创建独立 `resume_helper` Conversation 并复用现有 SSE/AgentRun/Artifact 链路。
- [x] 新增 workspace + agent scoped 历史查询，以及 `/analyses` GET 和 `/{run_id}` DELETE。
- [x] 删除单次历史时级联清理该分析 Conversation，同时保留 workspace 简历附件和其他记录。
- [x] 在 `app.main.create_app` 注册路由。

## 4. Resume Helper Executor

- [x] 为 `resume_helper` 增加专用 AgentSpec、ContextPolicy、system prompt、executor id 和 skill 声明。
- [x] 调整 `ContextBuilder`，让 `resume_helper` 使用明确选择简历的全部文本块。
- [x] 新增严格的 `ResumeAnalysisOutput` 及子模型。
- [x] 新增确定性 Markdown renderer，覆盖问题、分模块建议、岗位匹配、课程能力映射和完整草稿。
- [x] 实现并注册 `ResumeHelperExecutor`，Artifact type 固定为 `resume_analysis`，保存输入快照和报告 schema version。
- [x] 覆盖缺少附件、无课程记录、通用分析、岗位定向分析、非法 JSON、模型失败和重试测试。

## 5. 前端 API 与状态

- [x] 在 `apps/web/src/api.ts` 定义 Resume Profile、分析请求、结构化报告和历史记录类型。
- [x] 增加 profile、分析 SSE、历史列表与删除 API 函数，复用统一错误与 SSE 解码约定。
- [x] 新增 `useResumeAssistant`，管理首次加载、当前简历、课程默认选择、上传、分析、重试、历史恢复和删除。
- [x] 保证未开始课程可见但禁用，已开始课程仅在首次加载时默认选中。

## 6. 学生工作台界面

- [x] 新增 `ResumeAssistantPanel`，实现上传状态、岗位/JD、课程证据选择、显式分析和结构化报告。
- [x] 实现完整草稿与分模块 Clipboard 复制反馈。
- [x] 新增 `ResumeAgentHistoryPanel`，复用教师端视觉模式，实现最近 6 条、展开全部、打开和二次确认删除。
- [x] 增加“模拟面试 · 即将上线”预留入口，确保不触发后端。
- [x] 更新 `StudentWorkspace` 桌面菜单、内容布局和内部简历会话过滤。
- [x] 更新移动端为四项导航，并将简历历史在窄屏下放到主区之后。

## 7. 回归与质量门

- [x] 运行后端简历助手单元/API/隔离/迁移测试。
- [x] 运行完整 API pytest，确认既有附件、课程、教师智能体和通用聊天未回归（结构校正回归补充后为 `147 passed, 1 deselected`）。
- [x] 在 `apps/web` 运行 `npm.cmd run lint`。
- [x] 在 `apps/web` 运行 `npm.cmd run build`。
- [x] 运行 `alembic upgrade head` 并确认只有一个迁移 head（`0014_student_resume_profile`）。
- [x] Docker 栈运行并通过 8080 完成真实上传、课程启动、模型分析、历史 Artifact、桌面和移动端烟测。Web 镜像已重建；API 完整镜像重建因本机 Docker 镜像代理持续返回 525 未完成，改用现有 API 镜像的源码卷与容器内 0014 迁移完成验证。
- [x] 修复模型偶发 `invalid_structured_output`：首次严格校验失败后做一次 JSON 模式结构校正；同一份 1651 字符 PDF 经 8080 代理在约 124 秒内生成 Artifact。Nginx API 流超时调整为 180 秒并通过 `nginx -t`；镜像重建受 Docker Hub token 网络超时阻断，运行容器已热加载同一版本化配置。
- [x] 执行 `trellis-check`，补充模型未选课程证据的硬校验，并通过规范、类型、测试和跨层数据流检查。

## 8. 规范与收尾

- [x] 使用 `trellis-update-spec` 记录简历助手的附件、课程证据、Artifact schema、历史和删除契约。
- [x] 更新任务实施清单与验证结果。
- [x] 用户确认后执行 Git 提交；提交保持为单一“学生简历助手”主题。
