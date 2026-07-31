# 学生课程中心实施计划

## Phase 1：数据库与领域模型

- [x] 新增 `0013` Alembic 迁移：课程元数据、章节、课程进度、章节进度、薄弱点和对话章节关联。
- [x] 扩展 SQLAlchemy 模型并确保 `app.main` 导入新模型。
- [x] 增加课程详情聚合、默认课程初始化、开始学习、完成章节和薄弱点刷新所需 Repository。
- [x] 为默认模板、所有权隔离、进度状态机和 Artifact 证据提取编写后端测试。

依赖：以仓库 revision `0012_campus_news_cache` 为迁移父节点；不处理运行环境中仓库缺失的外部 revision。

## Phase 2：API 与共享契约

- [x] 扩展 Course 请求/响应模型，保持教师端现有 CRUD 兼容。
- [x] 实现 `POST /api/courses/defaults`。
- [x] 实现 `GET /api/courses/{course_id}`。
- [x] 实现 `POST /api/courses/{course_id}/start`。
- [x] 实现章节选择/开始和 `POST .../complete`。
- [x] 扩展创建对话契约以接收并校验 `chapter_id`。
- [x] 同步 `apps/web/src/api.ts` 类型与请求函数。

依赖：Phase 1 数据模型与 Repository 已完成。

## Phase 3：课程中心与详情页

- [x] 新增课程中心卡片网格组件，包含缩略图、课程名、开课时间、教师、进度和学习按钮。
- [x] 新增课程详情组件，包含章节、进度、薄弱点、推荐和学习按钮。
- [x] 扩展学生端左侧菜单及移动端可达导航。
- [x] 实现卡片主体进入详情、内部按钮直达学习的无冲突交互。
- [x] 实现加载、错误、重试和无薄弱点空态。

依赖：Phase 2 API 契约稳定。

## Phase 4：AI 学习工作台课程/章节上下文

- [x] 扩展 `CourseContext` 与 `useWorkspaceChat`，创建对话时携带章节。
- [x] 学习工作台显示当前课程和章节。
- [x] 增加“完成本节学习”动作并刷新课程进度。
- [x] 确保课程切换时对话、资料和成果不会跨课程/章节串用。

依赖：Phase 2 完成章节 API；Phase 3 提供课程和章节选择状态。

## Phase 5：验证与交付

- [x] 运行后端 pytest 与直接相关迁移检查。
- [x] 运行前端 lint 和 production build。
- [x] 使用 `docker compose up -d --build` 构建并运行，检查 API、Web、数据库状态。
- [x] 手动验证默认课程、详情、开始/继续、章节完成和刷新后持久化。
- [x] 执行 Trellis quality check，更新任务记录。
- [x] 用户已明确要求提交 Git；仅提交本任务相关文件，提交前检查不包含环境文件、构建产物或无关改动。

依赖：Phase 1–4 全部完成。
