# 分层智能体意图路由技术设计

## 1. 目标与约束

自动路由按固定顺序执行：角色白名单 -> 语义候选召回 -> Intent LLM 结构化判定 -> 确定性输入检查 -> 单智能体执行或普通聊天降级。手动选择仍然直接命中角色白名单，不调用 Embedding 或 Intent LLM。

本设计复用现有 OpenAI-compatible Embedding Provider 和 Chat Provider，不新增模型配置、数据库表、前端确认流程或多智能体编排。`RouteDecision`、AgentRun、REST 和 SSE 的字段形状保持兼容。

## 2. 声明式路由画像

在 `apps/api/app/agents/registry.py` 为 `AgentDefinition` 增加不可变的 `RoutingProfile`：

- `intent`：该智能体负责解决的问题，而不是实现描述。
- `examples`：多条代表性用户表达，用作语义召回原型。
- `exclusions`：与相邻智能体的边界和不负责事项，供 Intent LLM 判定。

所有 18 个已注册智能体都必须有非空画像。新增普通智能体只需增加一个声明即可参与自动路由；需要专用执行逻辑时，仍按既有 `AgentSpec`、InputContract、ContextPolicy 和 Executor 边界实现。测试负责保证角色内 id 唯一、画像完整，并防止新增智能体遗漏路由元数据。

## 3. 语义候选召回

新增独立候选召回模块，例如 `apps/api/app/agents/intent_retrieval.py`，避免 AgentRouter 直接依赖具体 Embedding SDK。

### 3.1 接口与结果

- `IntentCandidateRetriever` Protocol 暴露异步 `retrieve(role, context, agents)`。
- `SemanticIntentRetriever` 依赖现有同步 `EmbeddingProvider`，通过 `asyncio.to_thread` 执行网络调用，避免阻塞事件循环。
- 内部候选包含 agent id 和相似度；Router 对外仍只暴露有序 `candidate_agent_ids`。

### 3.2 索引与评分

- 每条 `examples` 与该 agent 的 `intent` 组合成一个语义原型。
- 原型向量按角色和画像指纹缓存在 API 进程内；同一进程内画像未变化时不重复生成。
- 用户当前内容作为主查询。仅对短追问加入有限的最近对话和当前会话智能体信息；原始附件正文不拼入语义查询，避免附件偶然内容压过用户当前指令。
- 对每个 agent 取其原型余弦相似度最大值作为召回分数，稳定排序后取 Top 3。
- 空向量、维度不一致、非有限数值、Provider 未配置或调用异常都视为召回不可用，不向调用方抛出业务错误。

当前每个角色只有 6 个智能体，进程内缓存足够；引入 pgvector 表会增加迁移和同步一致性，却没有带来可验证收益，因此本期不持久化意图向量。

## 4. AgentRouter 决策流

1. 获取当前角色白名单；无可用智能体时沿用 `role_not_supported`。
2. 手动 agent id 通过角色校验后直接返回 `selection_source=manual`。
3. Chat Provider 未配置时直接返回普通聊天降级，不执行语义召回。
4. 调用语义召回取得 Top 3；若失败，候选退化为当前角色全部智能体。
5. Intent LLM Prompt 只包含候选画像、当前消息、最近上下文和结构化附件事实。原始文件不发送给分类器。
6. 使用 `parse_json` 校验 `agent | null`、`confidence`、`reason`。自动判定只允许一个 agent。
7. 返回的 agent 必须属于本次候选集合；候选外 id、非法 JSON、空响应或异常统一视为分类失败。
8. agent 非空且置信度达到现有阈值 `0.8` 时才执行专家智能体。缺失输入继续由程序基于当前上下文计算，不以模型猜测替代确定性检查。
9. agent 为空、低置信度或分类失败时返回 `agent=None`、`requires_confirmation=False`，进入普通聊天，不触发专家执行器。

`selection_source` 使用现有长度限制内的稳定值：

- `manual`：用户明确选择。
- `semantic_llm`：语义召回成功后由 Intent LLM 选择。
- `llm_fallback`：语义召回不可用，Intent LLM 在角色全部智能体中选择。
- `fallback`：未选择专家，进入普通聊天。

成功决策的 `candidates` 保留本次有序候选集合，而不只保留最终 agent，以便 AgentRun 和路由 API 记录召回范围。`reason` 使用模型的简短判定理由；故障降级使用稳定的程序理由，不写入异常详情、Prompt、向量或密钥。

## 5. 应用接线

- `app.main.create_app` 创建一个进程级 `SemanticIntentRetriever` 并放入 `app.state`，复用同一 Embedding Provider 和画像缓存。
- FastAPI dependency 返回该 Retriever；路由查询、消息流和 AgentRun 重试统一构造相同的 AgentRouter。
- `/route` 当前只注入 Chat Provider，需要同步接入 Retriever；消息流和重试路径同样使用统一依赖，避免不同入口行为漂移。
- 测试通过 Fake Retriever、Fake Embedding Provider 和 Fake Chat Provider 注入结果，不访问真实模型服务。

## 6. 兼容性与回滚

- REST/SSE 字段不增删，前端无需改动；`selection_source` 增加新字符串值，但字段本身一直是开放字符串。
- AgentRun 的 `selection_source` 为 `String(16)`，新值均满足长度约束；候选继续写入现有 JSON 字段，因此无需迁移。
- 旧规则函数和规则置信度映射在新路径稳定后删除，避免两套自动路由产生分歧；正确业务案例由回归测试保留。
- 回滚只需恢复旧 Router 和 API 接线；没有数据库或持久化索引需要清理。

## 7. 风险控制

- 相近意图误召回：每个画像提供正向例子和排除边界，Top 3 后仍由 Intent LLM 判定，并覆盖 PPT/教案/学情等历史冲突案例。
- 首次请求延迟：按角色批量生成原型并缓存；后续只嵌入查询文本。
- 多 worker 缓存重复：每个进程各自缓存，数据量很小且避免跨进程同步复杂度。
- 外部服务波动：Embedding 失败扩大候选，Chat 分类失败降级普通聊天，均不阻断消息流。
- 模型越权：程序在结构化解析后再次校验候选白名单，候选外结果不得执行。
