# 分层智能体意图路由实施计划

## 实施清单

- [x] 扩展 `apps/api/app/agents/registry.py`：定义 RoutingProfile，为三个角色的全部智能体补齐 intent、examples 和 exclusions。
- [x] 补充注册表契约测试：角色内 id 唯一、画像字段完整、新增智能体不会遗漏语义元数据。
- [x] 新增语义候选召回模块：Protocol、候选结果、原型构建、余弦评分、稳定 Top 3、画像指纹和进程内缓存。
- [x] 为召回模块补单元测试：排序、角色隔离、短追问上下文、缓存复用、无配置、异常、空/非法/维度不一致向量。
- [x] 重写 `apps/api/app/agents/router.py` 自动路径：删除集中式关键词评分，接入候选召回与候选受限的 Intent LLM 判定。
- [x] 保留手动选择、角色白名单、确定性缺失输入和普通聊天行为；保证所有自动低置信度/异常路径 `requires_confirmation=False`。
- [x] 加固结构化输出校验：候选外 agent、非法 JSON、空响应、低置信度均不得触发专家执行器。
- [x] 在 `app.main` 和 FastAPI dependencies 中创建/提供进程级 Retriever，并统一接入 route、stream 和 retry 三条调用路径。
- [x] 更新 Router 单元测试，覆盖明确意图、相近意图、普通聊天、短追问、附件事实、手动选择、候选外输出及双层故障降级。
- [x] 更新 API 回归测试，验证 RouteResponse、SSE、AgentRun 候选与 selection_source，同时确保现有调用方字段不变。
- [x] 运行 PRD 收敛复查、代码规范检查和全量 API 单元测试；确认没有数据库模型或 Alembic 变化。

## 验证命令

在 `apps/api` 执行：

```powershell
..\..\.venv\Scripts\python.exe -m pytest tests/core/test_agent_router.py tests/core/test_intent_retrieval.py tests/api/test_stage5_routing.py
..\..\.venv\Scripts\python.exe -m pytest
```

在仓库根目录执行：

```powershell
git diff --check -- .env.example apps/api .trellis/tasks/07-30-layered-agent-intent-routing
git status --short
```

测试必须使用 Fake Provider；不得为了验收调用真实 Embedding 或 Chat 服务。

## 风险文件与回滚点

- `apps/api/app/agents/registry.py`：18 个画像是召回质量基线；遗漏会使智能体无法参与自动路由。
- `apps/api/app/agents/router.py`：核心行为切换点；先以测试锁定历史正确案例，再删除旧规则实现。
- `apps/api/app/api/conversations.py`、`apps/api/app/api/agent_runs.py`：三条入口必须使用同一 Retriever，否则重试与首次请求会漂移。
- `apps/api/app/main.py`：只创建惰性 Retriever，不在启动阶段发起外部模型调用。

回滚时恢复旧 Router 和依赖接线即可；本任务没有迁移、数据库数据或外部索引清理步骤。

## 开始实施前检查

- [x] 用户确认 PRD、设计和实施计划。
- [x] 运行 `task.py start` 将任务切换到 `in_progress`。
- [x] 加载 `trellis-before-dev` 的后端规范后再修改业务代码。
