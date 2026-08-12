# Technical Design

## Overview

本次修复复用现有数据库会话归属，不增加迁移。后端负责学生可见 assistant 文本的统一品牌归一化；前端负责从服务器会话列表恢复课程/章节上下文，并通过纯函数生成角色与课程驱动的推荐问题。

扩展需求继续复用现有课程和 Attachment 边界，但增加 Attachment 的知识库同步状态迁移。Conversation 的 `course_id/chapter_id` 是服务端权威绑定；流式请求中的同名字段只用于检测前端是否仍处于相同课程上下文。

## Course Metadata Context

`StudentCourseService` 根据 workspace、Conversation.course_id 和 Conversation.chapter_id 生成结构化课程上下文。该上下文同时进入路由与 `ContextBuilder`：

- 路由把课程元数据视为 `course_qa` 的最小有效输入，因此无教材时不触发附件缺失错误；
- `ContextBuilder` 把课程名称、简介、分类、章节标题、章节摘要和知识点追加到 system message；
- 课程资料存在时，课程元数据与检索片段共同使用；不存在时只允许概览和基础导学，禁止声称引用教材。

前端流式请求发送 `course_id` 和 `chapter_id`。后端先与 Conversation 绑定比较，再从数据库取真实内容；不信任前端传来的课程名称、章节名称或知识点。

## Course Textbook and DeepTutor Knowledge Base

课程教材沿用 `POST /api/workspaces/current/attachments?course_id=...`。本地对象保存、文档解析、MaterialChunk 构建成功后执行 DeepTutor 同步：

1. 稳定名称为 `campus-course-{course UUID hex}`；
2. 调用 `/api/v1/knowledge/list` 检查知识库；
3. 不存在时 multipart POST `/api/v1/knowledge/create`，存在时 POST `/api/v1/knowledge/{name}/upload`；
4. 保存返回的 task ID 和 `queued` 状态到 Attachment；
5. DeepTutor 失败只更新知识库状态，不覆盖 Attachment 本地解析状态。

Attachment 新增 `knowledge_base_name/status/task_id/message`。这组字段描述外部知识库同步，不复用本地 `status/status_message`，避免两个异步流程互相覆盖。

学生端课程学习页提供显式“上传课程教材”入口。选中课程时，composer 的附件上传也使用 workspace scope；上传返回只在原课程仍为当前课程时合并。`useWorkspaceChat` 继续把当前课程全部 workspace attachments 默认选中。

## Data Flow

### Course conversation restoration

1. `useWorkspaceChat` 加载按 `updated_at` 倒序排列的 Conversation 列表，并暴露列表加载完成状态。
2. `App` 使用 `sessionStorage` 记录刷新前激活角色，整页刷新时复用现有按角色 `localStorage` token，并通过 `GET /api/workspaces/current` 校验后进入同一匿名 workspace；主动切换角色时移除激活角色标记。
3. `StudentWorkspace` 初次加载时从非简历助手的课程 Conversation 中选择最近更新项。
4. 前端读取该 Conversation 的 `course_id`、`chapter_id`，通过 `GET /api/courses/{course_id}` 恢复真实课程详情，再调用 `openConversation(id)` 加载消息与资源。
5. 用户主动进入课程/章节时，调用现有 start endpoint 获取最新进度，然后在本地 Conversation 列表中选择相同 `course_id + chapter_id` 的最近项；没有匹配项时仅清空活动消息，首次发送沿用现有 `createConversation(courseId, chapterId)`。
6. 最近对话弹窗点击课程 Conversation 时走同一恢复函数，避免只加载消息但保留错误课程上下文。

所有异步课程恢复使用递增版本号或 Abort/ignore guard。完成旧请求时先校验版本，防止快速切换课程造成上下文回滚。

## Frontend Boundaries

新增学生学习纯函数模块，集中拥有以下规则：

- 过滤非学生聊天 Conversation；
- 选择最近课程/章节 Conversation；
- 从 `TutorRoleId + CourseDetail/CourseChapter` 构建三条推荐问题；
- 将内部角色提示与用户可见问题分离/投影，避免组件内重复字符串解析。

`StudentOrbitHome` 只接收或调用上述派生结果并渲染，不直接重新实现筛选规则。推荐问题使用课程名、章节名和首个知识点作为可用上下文；缺失字段时逐级降级到课程或通用角色模板。

最近对话继续使用单一模态实例和现有响应式结构。列表为课程对话显示课程名与章节名；无法找到已删除课程时显示安全的“课程已不可用”状态，不把其他课程设为上下文。

## Brand-safe Streaming Boundary

在 `app.services` 增加无状态完整文本归一化函数和有状态流式归一化器：

- 识别大小写不敏感的 `DeepTutor`、`Deep Tutor` 及紧邻“助手/助教”变体；
- 学生可见替换为“智汇校园”或“AI 学伴”，保留其余回答正文；
- 流式归一化器缓存可能构成受控词的尾部前缀，只有确认不是受控词后才输出，因此品牌跨 delta 拆分时也不会短暂泄漏；
- 流结束时 flush 缓存；最终 `AgentResult.text` 使用同一完整文本函数归一化后再持久化；
- `streamed_text` 比较基于已归一化文本，避免最终补发重复回答。

归一化只在 `role == "student"` 的对话流启用。工程 API、日志和非学生工作流保持原值。

## Compatibility

- Conversation schema 和 API response 保持不变，无 Alembic 迁移。
- 已持久化的旧 assistant 消息可能仍含内部品牌；学生历史读取时前端保留一层显示归一化兼容旧数据，新写消息由后端保证干净。
- 现有 SSE event 名称和 payload 结构不变；仅 `delta.text` 内容经过学生品牌归一化。
- 不新增运行时依赖。前端使用现有 `tsx` 和 Node test runner 执行纯函数测试。

## Error and Rollback Behavior

- 恢复课程详情失败时保留课程列表和最近对话弹窗，显示现有 `courseError`，不得打开错误 Conversation。
- 恢复目标课程不存在时不回退到其他课程；允许用户删除该历史或选择有效课程。
- 品牌归一化器异常不得暴露原始内部品牌；实现为无 I/O、确定性字符串转换，并用分片属性用例覆盖。
- 回滚时可独立撤销前端恢复辅助函数和后端输出过滤器；因无 schema 变化，不需要数据库回滚。
