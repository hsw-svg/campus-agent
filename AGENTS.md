<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

# Campus Agent 项目规范

## 项目边界

- 当前聚焦校园 AI 工作台：React 前端、FastAPI 服务、PostgreSQL + pgvector、Alembic、本地对象存储和模型适配器。
- 未明确提出需求前，不新增账号、登录、JWT、班级、工作区、对话或角色权限等业务能力。
- 修改应保持在所属模块内，避免无关重构、格式化和范围扩张。

## 目录职责

- `apps/api`：Python 3.11+ FastAPI 服务、数据库访问、集成适配器和 pytest。
- `apps/web`：React 19、TypeScript、Vite、Tailwind CSS、lucide-react、Motion、Fetch/SSE；当前没有独立前端测试框架。
- `infra`：Docker、Nginx、PostgreSQL 初始化配置。
- `packages/contracts`：前后端共享契约；API 输入输出变化优先在此定义或同步。
- `storage`：本地运行期对象存储，不提交实际文件。
- `docs`：架构、规格和实施计划，仅在需求或设计变化时更新。

## 后端规范

- 应用工厂保持为 `app.main.create_app`；路由放在 `app.api`，业务编排放在 `app.services`，外部服务实现放在 `app.integrations`。
- 配置通过 `app.core.config.Settings` 获取；不得把密钥、数据库地址或模型配置硬编码。
- `.env.example` 只能提供非敏感模板；本地密钥和地址通过环境变量或本地 `.env` 提供。
- 使用 SQLAlchemy 和 Alembic 管理数据库结构；schema 或扩展变化必须配套迁移，不手工修改运行中的数据库。
- 对外错误沿用 `AppError` 的稳定 JSON 结构；健康接口故障应返回降级状态，不应导致进程退出。

## 前端规范

- 优先使用现有 React 19、TypeScript、Vite、Tailwind CSS、lucide-react 和 Motion 依赖，不引入功能重复的框架或组件库。
- 组件使用 `.tsx`，共享 API/SSE 契约集中在 `src/api.ts`，状态逻辑优先复用 `src/hooks/useWorkspaceChat.ts`。
- 前端本地开发端口为 `3000`；Compose 中由 Nginx 暴露为 `8080`。

## 本地运行与验证

```powershell
# 完整栈
docker compose up -d --build

# 容器化开发模式：首次或依赖变化时构建一次
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 容器化开发模式：仅修改 apps/api/app 或 apps/web/src 时无需重建
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# API
cd apps/api
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd apps/web
npm.cmd run dev
```

- API 单元测试：在 `apps/api` 执行 `..\..\.venv\Scripts\python.exe -m pytest`。
- 数据库集成测试：执行 `..\..\.venv\Scripts\python.exe -m pytest -m integration tests/integration`，需要 PostgreSQL + pgvector。
- 前端验证：执行 `npm.cmd run lint` 和 `npm.cmd run build`；仓库当前未配置独立前端测试脚本。
- 新功能和缺陷修复优先补充可执行回归；配置、脚本和文档变更至少运行直接相关的验证。
- 涉及迁移时执行 `alembic upgrade head`，并确认集成环境中的 pgvector 可用。

## 容器化开发规范

- `docker-compose.yml` 是生产/演示模式：`app` 使用 `production` 镜像目标，React 以静态文件由 Nginx 托管。
- `docker-compose.dev.yml` 是本地容器开发覆盖配置，必须通过 `docker compose -f docker-compose.yml -f docker-compose.dev.yml ...` 使用，不得把开发 target 写回生产 Compose。
- 开发模式仍保持单一 `app` 容器：DeepTutor 监听容器内 `127.0.0.1:8001`，FastAPI 监听容器内 `127.0.0.1:8000`，Vite 监听容器内 `127.0.0.1:3000`，Nginx 对外只暴露项目端口 `8080`。
- 开发模式的仓库相对路径挂载必须保持以下边界：
  - `./apps/api/app:/app/app:ro`
  - `./apps/api/alembic:/app/alembic:ro`
  - `./apps/api/alembic.ini:/app/alembic.ini:ro`
  - `./apps/web/src:/web/src:ro`
  - `./apps/web/index.html:/web/index.html:ro`
  - `./apps/web/vite.config.ts:/web/vite.config.ts:ro`
  - `./infra/docker/nginx.dev.conf:/etc/nginx/conf.d/default.conf:ro`
- 开发入口脚本按 DeepTutor → FastAPI → Vite → Nginx 顺序启动；DeepTutor、FastAPI、Vite 或 Nginx 任一关键进程退出时，入口脚本必须终止容器并转发停止信号。
- `CAMPUS_DEV_MODE=true` 时 FastAPI 使用 Uvicorn `--reload --reload-dir /app/app`，前端使用 Vite HMR；仅修改上述源码路径不需要重新构建或重启容器。
- 修改 `package.json`、npm 依赖、Dockerfile、Python 依赖或镜像运行时后，必须重新执行开发模式的 `up -d --build`；不要把主机 Windows `node_modules` 挂载进 Linux 容器。
- 开发模式验证至少执行 `docker compose -f docker-compose.yml -f docker-compose.dev.yml config`、后端 Compose 配置测试、`npm.cmd run lint`、`npm.cmd run build`，并确认 `docker compose ... ps` 中 `app` 为 `healthy`。
- 不得为开发热更新发布 `8001` 或让浏览器直接访问 DeepTutor；浏览器请求仍必须经过 Nginx → FastAPI → `127.0.0.1:8001`。

## 版本控制与安全

- 开始前检查 `git status`，保留用户已有未提交改动；不得使用 reset、checkout 等方式覆盖或删除用户改动。
- 不提交 `.env`、密钥、`node_modules`、`.venv`、构建产物、缓存或 `storage` 数据。
- 提交保持单一主题，提交前运行与变更范围相称的验证，不混入无关文件。
- 未经用户明确确认，不自动执行 Git 提交。
