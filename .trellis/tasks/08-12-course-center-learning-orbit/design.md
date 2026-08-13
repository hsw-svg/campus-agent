# 技术设计：课程中心与星球学习中心联动

## 1. 边界与原则

- `StudentCourseProgress` 继续作为课程是否开始及课程进度的唯一事实来源。
- Tutor 是交互教材内容源；本地 `Course` / `CourseChapter` 保存稳定绑定和前端所需投影，浏览器不直接访问 Tutor。
- 模板课程继续由 `ensure_defaults()` 幂等初始化；学习中心只消费 `started` 投影，不再使用“第一门课程”兜底。
- 课程总览、课程章节视图和对话视图是学习中心内部状态，不新增第二套导航。

## 2. 数据模型

新增 Alembic 迁移 `0016`：

- `course.deeptutor_book_id: varchar(96), nullable, index`：课程绑定的 Tutor 书籍。
- `course_chapter.deeptutor_chapter_id: varchar(96), nullable`：Tutor 目录章节标识。
- `course_chapter.deeptutor_page_ids: JSON/JSONB, non-null, default []`：章节可进入的 Tutor 页面标识；前端默认使用首个页面作为入口。
- 约束：同一工作空间内一个 Tutor 书籍最多绑定一门课程；同一课程内 Tutor 章节标识唯一（允许空值）。

不新增学习清单表、教材状态表或手工章节表。Tutor 创建调用保持同步事务边界：外部创建成功后再在一个本地事务中绑定课程和同步章节；本地事务失败返回错误但不得生成部分本地投影。

## 3. 后端契约

### 3.1 课程响应

扩展共享课程响应：

- `CourseSummaryResponse.deeptutor_book_id: string | null`
- `CourseChapterResponse.deeptutor_chapter_id: string | null`
- `CourseChapterResponse.deeptutor_page_ids: string[]`

`CourseDetailResponse` 继承上述字段。前端类型在 `apps/web/src/api.ts` 同步。

### 3.2 创建并绑定教材

新增学生专用接口：

`POST /api/courses/{course_id}/textbook`

请求：

```json
{
  "topic": "线性代数基础",
  "use_course_materials": true
}
```

行为：

1. 校验学生工作空间、课程归属、主题非空、课程尚未绑定 Tutor 书籍。
2. 当 `use_course_materials=true` 时，仅在该课程存在 `knowledge_base_status=ready` 的附件时传入 `course_knowledge_base_name(course_id)`；否则返回 `course_materials_not_ready`，不静默忽略用户选择。
3. 组合课程名称、说明和用户主题为 Tutor `user_intent`，复用 `DeepTutorClient.create_or_compile_book()`。
4. 通过统一解析器验证 `book.id`、`spine.chapters[].id/title/page_ids`；忽略 Tutor 自动生成的“本书导览”章节作为课程章节，但保留实际教学章节。
5. 自建零章节课程：按 Tutor `order` 创建本地章节，`learning_objectives` 写入 `knowledge_points`，`summary` 写入章节摘要。
6. 已有章节课程：不删除章节、不改位置和完成记录；按顺序为现有章节写入 Tutor 章节及页面映射，额外 Tutor 章节不写入本地，以避免改变模板课程结构。
7. 绑定 `deeptutor_book_id` 并提交；返回完整 `CourseDetailResponse`。

稳定错误：`course_textbook_exists`、`course_materials_not_ready`、`deeptutor_unavailable`、`deeptutor_invalid_response`。外部创建成功但本地保存失败时记录结构化日志，返回稳定 500；后续运维可按返回/日志中的 `book_id` 清理孤儿书籍。

### 3.3 服务职责

- 路由放在 `app.api.courses`，仅负责鉴权、输入输出和错误映射。
- 新建 `app.services.course_textbooks.CourseTextbookService` 编排 Tutor 调用与本地同步。
- `app.integrations.deeptutor.client` 继续负责上游 HTTP；新增的目录解析函数集中在服务/集成边界，测试不在多个消费者重复解析原始 JSON。
- `StudentCourseService` 继续负责课程详情、开始与进度投影，扩展响应字段但不承担外部调用。

## 4. 前端状态流

### 4.1 课程加载

- `refreshCourses()` 仍先调用后端幂等模板初始化，返回模板与自建课程的完整后端列表。
- 派生 `learningCourses = courses.filter(course => course.started)`，只把该列表传给学习中心。
- 移除首次加载自动恢复最近课程对话；最近对话弹窗仍可显式恢复，满足历史连续性。

### 4.2 学习中心视图状态

`StudentWorkspace` 维护：

- `learningCourse=null`：课程总览。
- `learningCourse!=null, learningChapterId=null`：课程章节总览。
- `learningChapterId!=null`：章节选中并启用课程对话上下文。

顶部“学习中心”始终重置为课程总览。点击已开始课程使用 `GET /courses/{id}` 加载详情，不调用 start；点击章节才调用现有章节 start 接口并恢复对应历史。返回总览清除当前课程/章节和聊天显示，但不删除持久对话。

### 4.3 星球呈现

- 课程总览：中央主星球为“我的学习星系”，外围节点为已开始课程；节点外使用 SVG/CSS `conic-gradient` 进度环，并以文本显示课程名和百分比。
- 课程视图：复用同一轨道组件渲染真实章节；不再使用 `fallbackStages`。
- 桌面保持三栏星图学习舱；移动端保持完整横向课程/章节轨道和 44px 触控目标；遵守 `prefers-reduced-motion`。
- 零学习课程和零章节课程分别提供明确空状态与课程中心/创建教材动作。

### 4.4 课程与教材创建

- 扩展 `CourseCenterPanel`：新增课程对话框，提交复用 `createCourse()`；保存后刷新课程并打开详情。
- 扩展 `CourseDetailPanel`：零章节课程主操作为“创建教材”，已有未绑定课程也可创建教材；已绑定则显示教材就绪状态。
- 新增课程教材创建对话框/面板：主题输入、是否使用已就绪课程资料、创建状态和错误；成功后刷新课程详情。
- 章节视图在 `deeptutor_page_ids[0]` 存在时显示“进入教材学习”；向 `StudentWorkspace` 传递 `bookId/pageId`，复用现有 `DeepTutorBookPanel initialBookId/initialPageId`。

## 5. 兼容性与安全

- 旧课程与旧章节迁移后绑定字段为空，现有课程、进度、对话和附件行为不变。
- 模板课程不会因 Tutor 目录同步而删除/重排章节。
- API 始终验证匿名工作空间课程归属；浏览器继续通过 Nginx → FastAPI → Tutor。
- Tutor 失败时不改变本地课程绑定；前端保留输入并允许重试。
- 不自动删除现有 Tutor 数据；真实回归只清理本次创建且可精确识别的数据。

## 6. 回滚

- 前端可独立回退到原学习中心渲染，新增响应字段为向后兼容可空字段。
- 后端可停止暴露教材创建接口而不影响既有课程读取。
- 数据库回滚删除新增索引/约束和三个映射字段，不触碰课程、章节和进度主数据。
