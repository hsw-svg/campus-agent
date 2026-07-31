# 学生简历助手技术设计

## 1. Scope

在现有学生工作台内新增独立的简历助手页面，并复用以下稳定链路：

```text
工作区附件上传
  → 当前简历指针
  → 真实课程进度快照
  → resume_helper Executor
  → AgentRun + Artifact
  → 右侧智能体记录
```

本任务是一个前后端、数据库和智能体契约共同组成的纵向功能，只有整体接通后才能独立验收，因此保持为单个 Trellis 任务，不拆分相互阻塞的子任务。

## 2. 页面与交互

### 2.1 导航

- `StudentWorkspace` 的桌面左侧菜单新增“简历助手”，与学习中心、课程中心、校园中心并列。
- 移动端底部导航同步增加“简历”，由三列调整为四列。
- `StudentSection` 增加 `resume`；进入后不渲染学习聊天输入框、课程详情或校园资讯。
- 学习中心的普通会话历史排除 `agent_id = resume_helper` 的内部分析会话，避免同一条记录同时出现在两个入口。

### 2.2 桌面布局

- 主区使用较宽的工作台布局：
  - 当前简历上传卡片及解析状态。
  - 可选目标岗位与职位描述。
  - 课程依据选择。
  - “开始分析”或失败后的“重新分析”。
  - 完整结构化报告与优化后简历草稿。
  - “模拟面试”预留卡片，显示“即将上线”，不触发请求。
- 右侧使用与 `TeacherAgentHistoryPanel` 一致的视觉语言：
  - 标题、记录数和执行状态。
  - 默认最近 6 条，支持展开全部。
  - 每条显示岗位、简历文件名、时间、状态和摘要。
  - 点击后在主区打开 Artifact；单条删除使用二次确认。
- 右侧只作为索引，不重复渲染完整报告。

### 2.3 移动端布局

- 主区优先显示上传、配置和报告。
- 智能体记录移到主区下方，保持相同的打开和删除能力。
- 岗位/JD、课程选择和草稿内容不得产生横向溢出。

### 2.4 当前简历

- 上传复用 `POST /api/workspaces/current/attachments`，前端 `accept` 仅列出 `.pdf,.docx,.txt,.md`。
- 上传返回后只有 `status in {indexed, degraded}` 且 `extracted_chars > 0` 才可设为当前简历。
- 扫描版 PDF 通常为 `degraded + extracted_chars = 0`，页面直接展示已有解析提示并禁止分析。
- 重新上传仅替换“当前简历”指针；旧附件仍由既有历史分析引用，不删除历史记录。

## 3. 数据模型

新增 `StudentResumeProfile`：

| 字段 | 约束 | 用途 |
| --- | --- | --- |
| `workspace_id` | PK，FK `anonymous_workspace.id`，级联删除 | 一个工作区只有一个当前简历入口 |
| `current_attachment_id` | nullable FK `attachment.id`，`SET NULL` | 指向当前简历附件 |
| `created_at` / `updated_at` | timezone datetime | 刷新恢复及状态展示 |

不新增独立分析结果表：

- 每次分析创建一个 `agent_id = resume_helper` 的独立 Conversation。
- 对应一次 AgentRun；成功时生成一个 `type = resume_analysis` 的 Artifact。
- 每个分析 Conversation 只承载本次请求和结果，因此删除历史时可删除整个 Conversation，并通过现有级联关系清理 Message、AgentRun 和 Artifact。
- 当前简历是 workspace-scoped Attachment，不属于分析 Conversation，因此删除历史不会删除当前简历。
- 所有数据最终随匿名工作区级联删除；不配置自动过期任务。

迁移版本从当前 `0013_student_course_center` 前进到新的单头版本，Alembic metadata 和应用启动模型导入同步注册 `StudentResumeProfile`。

## 4. API 契约

新增 `/api/resume-assistant` 路由，所有接口必须要求当前角色为 `student`。

### 4.1 当前简历

```text
GET /api/resume-assistant/profile
PUT /api/resume-assistant/profile
```

`PUT` 请求：

```json
{
  "attachment_id": "uuid"
}
```

校验：

- 附件属于当前工作区。
- 附件为 workspace scope，`conversation_id` 和 `course_id` 均为空。
- 扩展名属于 PDF、DOCX、TXT、Markdown。
- 已完成可用文本解析，`extracted_chars > 0`。

稳定错误包括：

- `resume_assistant_forbidden`
- `resume_attachment_not_found`
- `resume_attachment_invalid_scope`
- `resume_attachment_type_invalid`
- `resume_attachment_text_unavailable`

### 4.2 发起分析

```text
POST /api/resume-assistant/analyses/stream
Content-Type: application/json
Accept: text/event-stream
```

请求：

```json
{
  "attachment_id": "uuid",
  "target_role": "可选，最多 160 字符",
  "job_description": "可选，最多 12000 字符",
  "selected_course_ids": ["uuid"]
}
```

边界：

- `attachment_id` 必须仍等于当前简历，防止多标签页使用已经被替换的旧入口发起新分析。
- 课程 ID 去重且限制数量；每门课程必须属于当前工作区并已创建 `StudentCourseProgress`。
- 未开始课程返回 `resume_course_not_started`，跨工作区或伪造 ID按 `course_not_found` 处理。
- 空课程列表合法，报告必须说明本次没有课程进度依据。
- 后端只读取请求中明确选中的课程；不把所有工作区课程隐式送入模型。

服务层为每门选中课程生成只读证据快照：

- 课程名称、分类和总进度。
- 已完成章节及其知识点。
- 当前章节。
- 真实存储的薄弱知识点和学习建议。

服务层把目标岗位、JD 和课程快照序列化为内部受控 JSON 用户消息；简历正文仍通过显式选择的 Attachment 进入 `ContextBuilder`。该消息被持久化，因此现有 AgentRun 重试可以使用完全相同的输入，不需要新增通用 AgentRun 字段。

SSE 沿用已有 `message_start`、`route_decision`、`tool_status`、`artifact`、`delta`、`done` 和 `error` 事件。
Docker Nginx 的 API 流读取/发送超时为 180 秒，以覆盖一次有界结构校正。

### 4.3 历史

```text
GET /api/resume-assistant/analyses
DELETE /api/resume-assistant/analyses/{run_id}
```

列表按 `AgentRun.created_at DESC` 返回当前工作区中 `agent_id = resume_helper` 的记录，响应包含：

- run/conversation id。
- 状态和错误摘要。
- 目标岗位、简历文件名。
- 可选 `resume_analysis` Artifact。
- 创建与更新时间。

删除时再次校验 workspace 和 agent id，并删除该次分析 Conversation。正在执行的记录不可删除，返回冲突错误。删除当前正在查看的记录后，前端回到最新一条可用记录或空状态。

## 5. 智能体契约

### 5.1 AgentSpec

为 `resume_helper` 配置专用：

- `executor_id = resume_helper`
- 明确选择附件为必需输入。
- 允许 workspace attachment。
- 禁止隐式使用未选择附件。
- 排除教师学情表等学习明细材料。
- 支持的简历附件类型由简历助手 API 负责更严格校验。

`ContextBuilder` 对 `resume_helper` 读取已选简历的全部文本块，而不是只取关键词排名前几块，避免遗漏教育经历或项目经历。

### 5.2 输出结构

新增严格 Pydantic 输出模型：

```text
ResumeAnalysisOutput
├── overall_summary
├── issues[]
│   ├── section
│   ├── severity: high | medium | low
│   ├── problem
│   ├── evidence
│   └── suggestion
├── section_suggestions[]
│   ├── section
│   ├── suggestions[]
│   └── rewrite_examples[]
├── course_capability_matches[]
│   ├── course_name
│   ├── progress_evidence
│   ├── capability
│   └── suggested_wording
├── job_match
│   ├── matched_keywords[]
│   ├── gap_keywords[]
│   └── guidance
├── optimized_resume_sections[]
│   ├── heading
│   └── markdown
└── evidence_notice
```

岗位/JD 未填写时，`job_match` 数组可为空，但字段仍保持稳定。Executor：

1. 解析内部受控请求 JSON。
2. 把课程证据和反虚构规则加入 system prompt。
3. 要求模型只输出严格 JSON。
4. 使用 `parse_json` 严格校验；首次结构无效时，携带原输出做一次 JSON 模式校正，
   只允许修正结构且不得改变事实或结论；第二次仍无效则失败。
5. 用确定性 renderer 生成完整 Markdown。
6. 返回 `resume_analysis` Artifact。

Artifact `data` 保存：

```json
{
  "schema_version": "resume_analysis.v1",
  "input": {
    "resume_attachment_id": "uuid",
    "resume_filename": "resume.pdf",
    "target_role": "可选",
    "job_description": "可选",
    "selected_courses": []
  },
  "report": {}
}
```

不得虚构事实主要通过三层约束：

- 只把当前简历与后端生成的课程快照送入模型。
- prompt 明确禁止新增项目、实习、证书、成绩和技能，并要求每条建议填写 evidence。
- 缺失信息统一写“待补充”；Artifact 保留输入快照，便于回看建议依据。

## 6. 前端状态与组件

新增：

- `useResumeAssistant(token)`：负责 profile、上传、课程默认选择、SSE 分析、历史、重试和删除。
- `ResumeAssistantPanel.tsx`：主内容表单和报告。
- `ResumeAgentHistoryPanel.tsx`：教师端风格的右侧记录。

`api.ts` 集中定义所有 Resume Profile、Input、Report、History 类型和 API 函数，不在组件中直接断言原始 JSON。

状态规则：

- 首次进入并行读取 profile、历史和默认课程。
- 已开始课程首次加载时默认全部选中；用户后续取消选择不因无关重渲染自动恢复。
- 上传成功后更新 profile，但不自动开始分析。
- 分析开始时插入/刷新运行状态；完成后以 Artifact 渲染报告。
- 失败保留表单、当前简历和选择，可原地重试。
- 点击历史时从响应中的 Artifact 恢复报告和当次输入摘要，不修改当前简历指针。
- 草稿整体和每个 `optimized_resume_sections` 模块都提供 Clipboard API 复制及可访问状态提示。

## 7. 错误与隐私

- 非学生角色统一返回 `403 resume_assistant_forbidden`。
- 所有 Attachment、Course、AgentRun、Conversation、Artifact 查询都同时约束当前 workspace。
- 工作区不存在、附件无文本、课程未开始、模型未配置、结构化输出无效分别显示可操作文案。
- JD 和简历正文均不写日志；日志只记录 ID、状态和数量。
- 模拟面试入口不创建 Conversation、AgentRun 或模型请求。

## 8. 验证设计

### 后端

- Profile 创建、替换、刷新恢复、跨工作区附件拒绝。
- 扫描 PDF/零文本、错误扩展名、错误 scope 拒绝且不调用模型。
- 已开始课程默认来源、明确选择、取消选择、未开始和跨工作区课程拒绝。
- Executor 严格 JSON、确定性 Markdown、完整草稿、`待补充`规则提示和 Artifact input snapshot。
- 成功 SSE、Artifact 持久化、列表排序、最近记录恢复。
- 失败 AgentRun 可使用相同输入重试。
- 删除单次记录级联清理分析 Conversation/Message/Run/Artifact，但保留当前简历附件和其他历史。
- 非学生角色和多工作区隔离。

### 前端

- `npm.cmd run lint`
- `npm.cmd run build`
- 浏览器验证桌面左侧菜单、主区 + 右侧记录、最近 6 条展开、历史恢复、删除确认、复制反馈。
- 浏览器验证移动端四项导航、历史下移和无横向溢出。

### Docker

- `docker compose up -d --build`
- `alembic upgrade head`
- 经 `http://localhost:8080/api` 验证 profile、上传、分析历史和删除代理链路。
