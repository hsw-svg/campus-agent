# 学生课程中心技术设计

## 1. Scope

本任务交付一条完整的学生课程学习链路：

1. 学生工作区进入课程中心。
2. 后端为当前学生工作区幂等初始化默认通识课程。
3. 课程卡片主按钮直接开始或继续学习，卡片主体进入课程详情。
4. 课程详情展示章节、真实进度和有依据的薄弱点推荐。
5. AI 学习工作台携带课程与章节上下文。
6. 学生明确完成本节后，后端持久化进度并根据该章节已有学习成果刷新薄弱点。

不在本任务中新增账号、班级、选课、教师分配或角色权限体系。当前匿名学生工作区即学习进度的所有者。

## 2. Existing capabilities to reuse

- `Course`、`GET/POST/PATCH/DELETE /api/courses` 已提供工作区范围内的课程所有权校验。
- `Conversation.course_id`、课程资料过滤和 `useWorkspaceChat(courseContext)` 已具备课程上下文链路。
- 学生端 `course_qa` 与 `personal_tutor` 会生成结构化 Artifact；其中 `personal_tutor.data.mistakes` 和 `practice` 可作为薄弱点与推荐依据。
- `StudentWorkspace` 已有学习中心/校园中心的视图切换，可扩展为课程列表、课程详情、课程学习三种状态。

## 3. Data model

### 3.1 Extend `course`

新增字段：

- `template_key: varchar(64), nullable`：默认课程稳定标识；与 `workspace_id` 建唯一约束。
- `teacher_name: varchar(120), nullable`
- `starts_at: timestamptz, nullable`
- `thumbnail_key: varchar(64), nullable`：受控视觉主题键，不存外部图片 URL。
- `category: varchar(64), nullable`

`template_key` 只用于幂等补齐默认课程。用户修改课程名称、教师或时间时不会改变该键。

### 3.2 `course_chapter`

- `id: uuid`
- `course_id: uuid`，级联删除
- `title: varchar(200)`
- `summary: text, nullable`
- `position: integer`
- `estimated_minutes: integer, nullable`
- `knowledge_points: json`
- 时间戳

约束：`(course_id, position)` 唯一。章节按 `position` 排序。

### 3.3 `student_course_progress`

- `id: uuid`
- `workspace_id: uuid`，级联删除
- `course_id: uuid`，级联删除
- `started_at: timestamptz`
- `last_studied_at: timestamptz`
- `current_chapter_id: uuid, nullable`
- 时间戳

约束：`(workspace_id, course_id)` 唯一。虽然课程已归属于工作区，仍保留 `workspace_id` 以便所有查询显式执行所有权隔离。

### 3.4 `course_chapter_progress`

- `id: uuid`
- `course_progress_id: uuid`，级联删除
- `chapter_id: uuid`，级联删除
- `started_at: timestamptz`
- `completed_at: timestamptz, nullable`
- 时间戳

约束：`(course_progress_id, chapter_id)` 唯一。

### 3.5 `student_course_weak_point`

- `id: uuid`
- `course_progress_id: uuid`，级联删除
- `chapter_id: uuid, nullable`
- `name: varchar(200)`
- `recommendation: text`
- `evidence_artifact_id: uuid, nullable`，删除 Artifact 时置空
- `updated_at`

薄弱点仅由当前课程/章节范围内的结构化学生 Artifact 生成。首版读取 `personal_tutor` 的 `mistakes` 与 `practice`；没有证据时返回空数组。后续测验结果可沿同一服务接口扩展。

### 3.6 Extend `conversation`

新增 `chapter_id: uuid, nullable`，外键指向 `course_chapter`，删除章节时置空。

创建对话时若提供 `chapter_id`：

- 必须同时提供 `course_id`。
- 课程必须属于当前工作区。
- 章节必须属于该课程。

这样 Artifact 可通过 Conversation 精确归属到课程章节。

## 4. Default course initialization

新增 `POST /api/courses/defaults`：

- 仅允许 `student` 工作区调用。
- 在一个事务中按 `template_key` 创建缺失课程及其章节。
- 已存在的模板课程和章节完全不更新，避免覆盖用户数据。
- 返回完整课程摘要列表。

默认课程：

- 大学英语
- 形势与政策
- 高等数学
- 大学计算机基础
- 大学体育
- 职业生涯规划

每门课程提供中性的教师称谓、开课时间、缩略图主题和 4–6 个基础章节，不包含具体学校身份。

## 5. API contracts

### Course summary

`GET /api/courses` 与初始化接口返回：

- 基础课程字段
- `teacher_name`
- `starts_at`
- `thumbnail_key`
- `category`
- `chapter_count`
- `completed_chapter_count`
- `progress_percent`
- `started`
- `last_studied_at`

### Course detail

新增 `GET /api/courses/{course_id}`，返回：

- Course summary
- 排序后的章节及章节完成状态
- 当前章节
- 薄弱知识点及推荐

### Start/continue

新增 `POST /api/courses/{course_id}/start`：

- 首次调用创建课程进度和首章进度。
- 后续调用只更新 `last_studied_at`，不重置已完成章节。
- 返回课程详情与当前章节。

### Complete chapter

新增 `POST /api/courses/{course_id}/chapters/{chapter_id}/complete`：

- 校验课程和章节所有权。
- 将章节标记完成。
- 当前章节移动到下一个未完成章节；全部完成时保留最后章节。
- 从该章节关联的 `personal_tutor` Artifact 刷新薄弱点。
- 返回更新后的课程详情。

## 6. Frontend state and navigation

`StudentWorkspace` 使用显式状态：

- `learning`
- `courses`
- `course-detail`
- `campus`

另维护：

- `selectedCourse`
- `selectedChapter`

课程中心首次加载调用默认课程初始化接口并渲染响应式卡片网格。卡片整体使用可聚焦按钮/链接语义进入详情；内部“开始学习/继续学习”按钮阻止冒泡并直达学习工作台。

详情页使用独立 `CourseDetailPanel`，展示课程头图、进度、章节列表、薄弱点和推荐。点击章节可将其设为当前章节并进入学习。

进入学习时构造：

```ts
{
  courseId,
  courseName,
  chapterId,
  chapterName,
  workflowId: 'student-course-learning',
  workflowName: '课程学习'
}
```

`useWorkspaceChat` 在创建对话时携带 `course_id` 与 `chapter_id`。学习工作台顶部显示当前课程/章节，并提供“完成本节学习”按钮。完成后刷新课程详情和卡片进度。

## 7. Thumbnail strategy

`thumbnail_key` 映射到前端受控的渐变、图标和装饰图形，形成真实缩略图区域：

- 不依赖外网图片。
- 不存储任意 HTML 或 CSS。
- 无学校或品牌标识。
- 未识别键使用稳定的默认主题。

## 8. Error and empty states

- 默认课程初始化或详情请求失败：页面内错误提示和重试按钮，不回退到伪造的前端数据。
- 未开始课程：进度为 0%，显示“开始学习”。
- 已开始但无完成章节：显示“继续学习”和当前章节。
- 无薄弱点证据：显示“完成章节学习或测验后生成针对性建议”的空态。
- 全部章节完成：显示 100% 和“继续复习”语义，但按钮文案仍按需求保持“继续学习”。

## 9. Migration and compatibility

新增 Alembic 迁移 `0013`，以仓库当前 `0012_create_campus_news_cache.py` 的 revision 为下游。所有新列先保持 nullable，避免破坏已有教师课程。

本地 Docker 数据库曾指向已弃用 PPT 分支的 `0012_artifact_presentation`，而当前分支从共同祖先独立演进。用户确认该 PPT 功能已弃用后，已将唯一 Alembic 版本标记强制回退到共同祖先 `0011_course_attachment_scope`，再由当前仓库正常执行校园资讯与课程中心迁移。旧 PPT nullable 列保留为无害冗余，未删除业务数据。

## 10. Verification

- API 单元测试：
  - 默认初始化幂等、仅学生可用、不覆盖已有数据。
  - 课程详情所有权隔离。
  - 首次开始与重复继续。
  - 章节完成和进度计算。
  - 薄弱点仅从同工作区、同课程、同章节 Artifact 生成。
  - 对话章节归属校验。
- 前端：`npm.cmd run lint`、`npm.cmd run build`。
- API：pytest；迁移可用时执行 Alembic upgrade。
- Docker：按用户要求执行 `docker compose up -d --build` 并检查服务状态；若仍命中已知数据库 revision 阻塞，保留证据并避免破坏性修复。
