# Campus Agent 开发规范

## 项目边界

- 当前为 Stage 1 运行基础设施：Vue 前端、FastAPI 健康服务、PostgreSQL
  + pgvector、Alembic、本地对象存储和模型适配器。
- 未明确提出需求前，不添加账号、登录、JWT、班级、工作区、对话或角色权限等
  业务能力。
- 修改保持在所属模块内，避免与需求无关的重构和格式化。

## 目录职责

- `apps/api`：Python 3.11+ FastAPI 服务、数据库访问、集成适配器和 pytest。
- `apps/web`：Vue 3 + TypeScript + Vite 前端和 Vitest 组件测试。
- `infra`：Docker、Nginx、PostgreSQL 初始化配置。
- `packages/contracts`：跨端契约；变更 API 输入输出时优先在此定义或同步。
- `storage`：本地运行期对象存储，不提交实际文件。
- `docs`：架构、规格和实施计划；仅在需求或设计变化时更新。

## 后端规范

- 应用工厂保持为 `app.main.create_app`；路由放在 `app.api`，业务编排放在
  `app.services`，外部服务实现放在 `app.integrations`。
- 设置通过 `app.core.config.Settings` 获取；不得把密钥、数据库地址或模型配置
  写死在代码中。
- `.env.example` 只提供非敏感模板。根目录 `.env` 用于 Docker Compose；直接从
  `apps/api` 启动 API 时，使用进程环境变量或 `apps/api/.env` 提供配置。
- 使用 SQLAlchemy 与 Alembic 管理数据库结构；任何 schema 或扩展变更都必须有
  对应迁移，不手工修改运行中数据库作为替代。
- 对外错误沿用 `AppError` 的稳定 JSON 结构；健康接口故障应返回降级状态而非
  让进程退出。

## 前端规范

- 使用 Vue 3、TypeScript、Vite、Pinia 和 Element Plus 的现有依赖，不额外引入
  功能重叠的 UI、状态或构建框架。
- 组件保持可测试：页面交互写入 `*.spec.ts`，优先测试用户可观察到的行为。
- 前端本地开发默认端口为 `5173`；Compose 中由 Nginx 暴露为 `8080`。

## 本地运行

```powershell
# 一键启动 API（8000）和前端（5173）
.\start.cmd

# API 单独运行，使用根目录 .venv
cd apps/api
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端单独运行
cd apps/web
npm.cmd run dev
```

完整本地栈使用 Docker Compose：`docker compose up --build -d`。健康接口为
`GET /api/health`，Compose 下通过 `http://localhost:8000/api/health` 访问。

## 测试与验证

在改动对应层后至少运行相关验证：

```powershell
# API 单元测试；默认排除 integration 标记
cd apps/api
..\..\.venv\Scripts\python.exe -m pytest

# 数据库集成测试，需要可用的 PostgreSQL + pgvector
..\..\.venv\Scripts\python.exe -m pytest -m integration tests/integration

# 前端测试和生产构建
cd apps/web
npm.cmd run test:run
npm.cmd run build
```

- 新功能和缺陷修复先写能失败的测试，再实现最小改动使其通过。
- 配置、脚本或文档变更至少运行直接相关的命令，并记录无法执行的外部依赖或
  环境限制。
- 涉及迁移时执行 `alembic upgrade head`，并在集成环境确认 pgvector 可用。

## 版本控制与安全

- 开始前查看 `git status`；保留用户已有的未提交改动，不重置、不覆盖、不删除。
- 不提交 `.env`、密钥、`node_modules`、`.venv`、构建产物、缓存或 `storage` 数据。
- 提交保持单一主题，提交前运行与变更范围相称的测试；不要把无关文件混入提交。
