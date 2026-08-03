# DeepTutor 上游核查

核查日期：2026-08-03

## 版本与运行方式

- 上游仓库：<https://github.com/HKUDS/DeepTutor>
- 当前稳定发布线核查为 `v1.5.8`。上游 README 给出的 Python 支持范围为 3.11–3.13，因此本项目容器不能继续使用当前 API Dockerfile 的 Python 3.14 基础镜像。
- CLI 文档：<https://github.com/HKUDS/DeepTutor/blob/main/deeptutor_cli/README.md>
- CLI 提供 `deeptutor serve --host ... --port ... --reload`；本项目生产容器使用 `--host 127.0.0.1 --port 8001`，不启用 reload。

## REST / WebSocket 契约

- API 路由注册：<https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/api/main.py>
- 交互式书本路由：<https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/api/routers/book.py>
  - `/api/v1/book/health`
  - `/api/v1/book/books`
  - `/api/v1/book/books/{book_id}`
  - `/api/v1/book/books/{book_id}/spine`
  - `/api/v1/book/books/{book_id}/pages/{page_id}`
  - 书本创建和页面编译使用 POST 路由。
- 知识库路由：<https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/api/routers/knowledge.py>
  - `/api/v1/knowledge/health`
  - `/api/v1/knowledge/list`
  - `/api/v1/knowledge/{kb_name}`
- 对话路由：<https://github.com/HKUDS/DeepTutor/blob/main/deeptutor/api/routers/chat.py>
  - 统一聊天 WebSocket 在 `/api/v1/chat`，消息包含 `message`、`session_id`、`kb_name`、`enable_rag` 等字段。
  - 书本专用 WebSocket 位于 book router 的 `/ws`，创建/确认/编译流程使用事件消息。

本项目适配层只暴露稳定的现有应用 API；具体上游路径、超时和 WebSocket URL 均集中在 `DeepTutorClient`，以便固定版本变化时只改一处。

## 环境变量

上游 README / Compose 配置核查：

- <https://github.com/HKUDS/DeepTutor/blob/main/.env.example>
- <https://github.com/HKUDS/DeepTutor/blob/main/docker-compose.ghcr.yml>

DeepTutor 使用 `LLM_BINDING`、`LLM_MODEL`、`LLM_API_KEY`、`LLM_HOST`、可选 `LLM_API_VERSION`，以及 `EMBEDDING_BINDING`、`EMBEDDING_MODEL`、`EMBEDDING_API_KEY`、`EMBEDDING_HOST`、`EMBEDDING_DIMENSION`。本项目现有聊天变量使用 `CHAT_*`，需要在容器启动时映射；embedding 的 endpoint 和 dimension 不能未经确认直接复用聊天 URL 或任意维度。

## 采用与不采用

- 采用 PyPI 固定版本 + 独立 venv，减少和现有 FastAPI 依赖的冲突。
- 采用 DeepTutor REST/WS Server，不调用 DeepTutor 内部 Python 函数。
- 不采用 DeepTutor 自带前端进程；现有 React 生产构建由同一容器内 Nginx 提供。
- 不公开 8001；只由现有 FastAPI 反向代理给浏览器。
