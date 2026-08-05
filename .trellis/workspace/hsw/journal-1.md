# Journal - hsw (Part 1)

> AI development session journal
> Started: 2026-07-17

---



## Session 1: 分层智能体意图路由

**Date**: 2026-07-30
**Task**: 分层智能体意图路由
**Branch**: `master`

### Summary

实现语义嵌入候选召回与现有 Chat 模型最终判定，统一路由、SSE 和重试入口，补齐降级回归与后端代码规范。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `c953b42` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: 学生课程中心

**Date**: 2026-07-31
**Task**: 学生课程中心
**Branch**: `master`

### Summary

新增真实课程卡片、课程详情、章节进度、证据驱动薄弱点与课程章节 AI 上下文；完成 Docker 迁移恢复和端到端验证。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `3378d29` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: 学生简历助手与结构化输出修复

**Date**: 2026-07-31
**Task**: 学生简历助手与结构化输出修复
**Branch**: `master`

### Summary

新增学生端简历助手、课程进度证据、分析历史和模拟面试预留；修复 PDF 分析时模型结构化输出偶发失效，并延长 Docker SSE 代理超时。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `72aac85` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 4: 完成课程PPT模板智能匹配

**Date**: 2026-08-03
**Task**: 完成课程PPT模板智能匹配
**Branch**: `master`

### Summary

接入AI科技与商业计划书两种开发模板，实现受控LLM选模、源页面复用和文本填充，并通过完整后端测试。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `9ca8cc6` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 5: 完成 DeepTutor 集成

**Date**: 2026-08-03
**Task**: 完成 DeepTutor 集成
**Branch**: `master`

### Summary

在 codex/deeptutor-integration 完成 DeepTutor 1.5.8 单容器集成：独立 venv、启动就绪检查、共享 LLM/embedding 配置、FastAPI HTTP/WebSocket 适配层、React 交互教材页面和持久化 Compose 卷；合并回 master。159 个 API 测试、前端 lint/build、Compose config 通过；Docker Hub 拉取受网络阻断。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `061a122` | (see git log) |
| `b455aac` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 6: 学生端 DeepTutor 学习空间

**Date**: 2026-08-03
**Task**: 学生端 DeepTutor 学习空间
**Branch**: `codex/student-deeptutor-learning-space`

### Summary

在学生工作台加入 DeepTutor 学习空间和交互教材阅读器：书架/目录/页面内容块/页面问答、进度笔记收藏，以及同源 API 归一化和移动端导航；完成前端 lint/build、后端 159 项测试和桌面移动冒烟。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `31387e9` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 7: 教师独立智能体入口

**Date**: 2026-08-04
**Task**: 教师独立智能体入口
**Branch**: `master`

### Summary

新增教师侧学情分析、课堂互动与课程迭代独立入口，支持覆盖式准备页、无课程任务执行、资料约束例外和交互稳定性优化，并统一课堂互动命名。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `5840de0` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 8: 教师独立 Agent 与历史栏修复

**Date**: 2026-08-05
**Task**: 教师独立 Agent 与历史栏修复
**Branch**: `master`

### Summary

修复教师独立 Agent 历史与新建任务状态、课程迭代成果持久化和流取消收口；兼容旧文本历史，并提交教师历史栏单实例响应式布局规范。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `5a4101e` | (see git log) |
| `97554dc` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 9: 课程切换驱动教师端快捷任务

**Date**: 2026-08-05
**Task**: 课程切换驱动教师端快捷任务
**Branch**: `master`

### Summary

为教师端快捷任务增加课程上下文派生文案；切换课程后统一更新欢迎区、学情报告操作区和输入区入口；补充前端状态规范，完成 lint/build 验证并提交。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `62dcb2b` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete
