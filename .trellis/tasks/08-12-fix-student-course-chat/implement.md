# Implementation Plan

## 1. Red-capable regression loops

- 新增课程上下文回归：服务端元数据注入、请求/Conversation 上下文不一致、无教材 `course_qa` 允许执行。
- 新增 DeepTutor multipart client 回归：稳定课程知识库首次 create、后续 upload、任务 ID 解析和上游失败映射。
- 新增课程教材 API 回归：Attachment 课程绑定、知识库状态持久化、DeepTutor 不可用时本地解析不回滚。
- 新增前端纯函数测试，先复现：课程/章节最近会话选择、刷新恢复目标、四角色推荐差异与上下文降级。使用现有 `tsx --test`，不新增测试框架。
- 新增后端 conversation stream 回归，先以 `Deep` + `Tutor助手发现……` 分片断言 SSE 和持久化内容都不含内部品牌。
- 运行新增测试确认修复前为红，并记录最小失败信号。

## 2. Student conversation restoration

- 在 `useWorkspaceChat` 暴露 Conversation 列表完成状态，保持 token/course 变化时的版本保护。
- 提取学生 Conversation 筛选和最近匹配选择纯函数。
- 在 `StudentWorkspace` 增加统一的 `restoreStudentConversation`，按 Conversation 恢复课程详情、章节、会话消息和学习会话状态。
- 初次刷新自动恢复最近课程 Conversation；用户主动选择课程/章节时恢复精确匹配的最近 Conversation。
- 完成章节后切到新 current chapter，并恢复该章节已有最近 Conversation；不存在时保持空状态。
- 最近对话弹窗展示全部非简历助手学生 Conversation，并通过统一恢复函数打开；补充课程/章节上下文标签和失效课程错误状态。

## 2.1 Course metadata and request integrity

- 扩展流式请求加入 `chapter_id`，前端与 `course_id` 一并提交。
- 后端比较请求上下文与 Conversation 持久绑定，不一致时在写入用户消息和调用模型前拒绝。
- `StudentCourseService` 构建受信任课程元数据；路由、ContextBuilder 和 CourseQAExecutor 共享同一上下文语义。
- 允许学生课程问答在无教材时使用课程元数据；保留 personal tutor 等其他智能体的附件要求。

## 2.2 Course textbook binding and DeepTutor sync

- 新增 Alembic 迁移与 Attachment ORM/API 字段，分离本地解析和知识库同步状态。
- 扩展 `DeepTutorClient` 支持 multipart create/upload，并以课程 UUID 生成稳定知识库名。
- 课程级 workspace upload 在本地解析后调用知识库同步；失败降级、不删除本地文件。
- 学生课程页增加显式教材上传入口；课程内 composer 上传自动使用 workspace scope。
- 保持当前课程附件自动加载、自动选择和异步切课保护。

## 3. Brand normalization

- 将学生角色提示改为品牌中立的回答风格指令，并移除学生角色菜单中的 DeepTutor 文案。
- 在 backend service 层实现完整文本与分片流式品牌归一化器。
- `role == "student"` 时，对 executor delta、最终补发 delta 和持久化 assistant message 使用同一归一化规则。
- 前端 `toUiMessage`/学生展示增加旧历史兼容归一化，避免旧记录刷新后泄漏。
- 覆盖大小写、空格、中文助手后缀和跨 delta 拆分。

## 4. Dynamic recommended questions

- 提取 `buildTutorRecommendedQuestions(role, course, chapter)` 纯函数。
- 为 default、peer、research-assistant、teacher 分别定义三条目的明确的模板；插入当前课程、章节和可用知识点。
- `StudentOrbitHome` 通过 `useMemo` 随角色/课程/章节更新按钮文案与提交 prompt，保留现有点击问答链路和图标。
- 无课程、无章节、长课程名和空知识点使用安全降级与可换行样式。

## 5. Validation

在 `apps/api`：

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/api/test_conversations.py tests/api/test_courses.py
```

在 `apps/web`：

```powershell
npm.cmd run test
npm.cmd run lint
npm.cmd run build
```

仓库级：

```powershell
git diff --check
```

若本地开发容器可用，再执行：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml config
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

并在桌面与窄屏各做一次学生学习中心手工烟测：课程 A 提问、切换课程 B、返回 A、刷新、从最近对话恢复、切换四角色检查推荐、模拟品牌分片回答。

## Review Gates

- 新增测试在实现前能捕获对应缺陷，在实现后转绿。
- 不新增 Alembic 迁移或第二套本地会话状态。
- SSE 协议字段不变，非学生流不受品牌替换影响。
- Impeccable UI 机械检测对改动目标运行一次，修复高置信问题后最多再确认一次。
- 所有自动验证通过后再进入 Trellis 质量检查；未经用户明确确认不执行 Git commit。
