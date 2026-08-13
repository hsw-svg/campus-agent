# 实施清单：课程中心与星球学习中心联动

## 1. 数据库与后端契约

- [x] 新增 `0016` 迁移：课程 Tutor 书籍绑定、章节 Tutor 目录/页面映射及安全唯一约束。
- [x] 更新 SQLAlchemy 模型、课程 API Pydantic 响应和前端共享类型。
- [x] 为旧课程、空映射和迁移 upgrade/downgrade 补充验证。

## 2. Tutor 教材绑定服务

- [x] 新建 `CourseTextbookService`，复用 `DeepTutorClient` 和课程知识库命名函数。
- [x] 集中解析并校验 Tutor `book/spine/chapters/page_ids` 响应，过滤自动导览章节。
- [x] 实现零章节课程创建章节、已有课程顺序映射且不破坏进度。
- [x] 新增 `POST /api/courses/{course_id}/textbook`，处理资料未就绪、重复绑定、上游故障和事务回滚。
- [x] 后端 API/服务测试覆盖：自建课程、课程隔离、资料就绪判断、成功同步、模板章节保留、无效响应、失败不半绑定。

## 3. 课程中心

- [x] 将学生课程加载保持为后端模板幂等初始化，不新增前端固定课程数组。
- [x] 在 `CourseCenterPanel` 添加学生创建课程入口、表单校验、加载/错误/成功状态。
- [x] 新建课程后打开真实课程详情；未开始课程不进入学习中心。
- [x] 在 `CourseDetailPanel` 增加创建/已绑定教材状态和 Tutor 教材创建交互。
- [x] 前端单元测试覆盖课程过滤、教材入口判定和 Tutor 响应投影。

## 4. 学习中心星球总览与章节视图

- [x] 移除首次进入自动选中最近课程；顶部学习中心始终进入课程总览。
- [x] 仅传入/渲染 `started=true` 课程，构建主星球 + 多课程轨道和进度光圈。
- [x] 点击课程只加载详情并切换章节星图，不改变开始时间或自动打开对话。
- [x] 删除固定章节兜底；零章节课程展示创建教材引导。
- [x] 点击章节使用现有 start 接口，绑定对话上下文并恢复对应历史。
- [x] 增加返回课程总览和“进入教材学习”动作，复用现有 Tutor 阅读面板。
- [x] 完成桌面、平板、390×844 窄屏和 reduced-motion 状态。

## 5. 自动化验证

- [x] API 全量：`cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest`。
- [ ] 数据库集成：`cd apps/api; ..\..\.venv\Scripts\python.exe -m pytest -m integration tests/integration`（PostgreSQL + pgvector 可用时）。
- [x] 迁移：`cd apps/api; ..\..\.venv\Scripts\alembic.exe upgrade head`，并确认应用健康。
- [x] 前端：`cd apps/web; npm.cmd test`（现有 Node test 脚本）、`npm.cmd run lint`、`npm.cmd run build`。
- [x] Impeccable 机械检查：对变更的学生端 TSX/CSS 运行一次 `detect.mjs --json`。

## 6. Docker 与真实 Tutor 回归

- [x] `docker compose -f docker-compose.yml -f docker-compose.dev.yml config` 及相关 Compose 配置测试。
- [x] 确认 `campus-agent-app-1`、数据库、独立 `deeptutor`、Neo4j 健康。
- [x] 创建独立匿名学生空间，确认课程中心保留模板课程。
- [x] 创建唯一命名自建课程，确认学习中心暂不可见。
- [x] 为课程上传小型教材文件，等待课程知识库 ready；用该知识库创建 Tutor 教材。
- [x] 验证本地课程绑定 `book_id`、章节同步、页面映射以及 Tutor 页面可打开。
- [x] 点击开始学习，验证课程总览出现进度光圈；选择章节并提问，确认课程/章节上下文正确。
- [x] 刷新、返回总览、切换课程、最近对话恢复，确认不串状态。
- [ ] 在浏览器桌面与 390×844 视口完成视觉/交互回归；最多一轮集中修复和一轮确认。
- [x] 清理本次测试工作空间及可安全精确删除的 Tutor 测试数据，复核容器健康。

## 7. 质量与收尾

- [x] 运行 `trellis-check`，检查规格、跨层数据流、类型、Lint、测试和差异范围。
- [x] 更新 `.trellis/spec/backend/student-course-center.md`、`deeptutor-integration.md`、`frontend/student-learning-continuity.md`。
- [x] `git diff --check`；向用户报告验证结果与任何外部 Tutor 残留数据。

## 风险与回滚点

- Tutor 建书可能耗时且产生孤儿书籍：本地绑定必须事务化，失败日志记录精确 `book_id`。
- 模板章节已有进度/对话引用：严禁删除或重排，只允许写入可空 Tutor 映射。
- 移除自动恢复不能破坏历史连续性：最近对话显式恢复必须保留回归测试。
- CSS 星球轨道容易在窄屏溢出：先保证课程名、百分比、章节和主操作可达，再保留装饰。
