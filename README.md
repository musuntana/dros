# DR-OS

DR-OS 是一个以 `Artifact -> Assertion -> EvidenceLink` 为主链路的医学科研工作台原型仓库。当前仓库已经能跑通本地联调、容器化启动和基础 smoke test，但它仍然是开发基线，不是生产系统。

## 它现在是什么

- 后端是 `FastAPI Control Plane`，当前实现 `61` 条 `/v1` 业务路由，外加 `GET /healthz`
- 前端是 `Next.js App Router` 工作区，已覆盖 `projects / datasets / workflows / analysis-runs / artifacts / assertions / evidence / manuscripts / reviews / exports / audit`
- 持久化支持 `memory / json / postgres` 三种 backend，其中 `postgres` 仍是开发态 snapshot adapter
- 本地部署支持 `docker compose --profile postgres up --build -d`

更完整的代码对齐状态见 [docs/implementation-status.md](docs/implementation-status.md)。

## 仓库结构

- `docs/`：架构、对象模型、API、事件、部署和实现状态文档
- `contracts/`：Agent 和事件 JSON Schema
- `backend/`：FastAPI Control Plane、service、repository、schema、脚本
- `frontend/`：Next.js Research Canvas、Gateway adapter、Server Action、E2E
- `sql/`：Research Ledger DDL 和本地 PostgreSQL 初始化脚本

## 快速开始

### 直接本地运行

后端：

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
CONTROL_PLANE_BASE_URL=http://127.0.0.1:8000 \
NEXT_PUBLIC_CONTROL_PLANE_BASE_URL=http://127.0.0.1:8000 \
npm run dev -- --hostname 127.0.0.1 --port 3000
```

### Docker Compose

```bash
cp .env.example .env
docker compose --profile postgres up --build -d
docker compose --profile postgres ps
```

访问入口：

- Frontend: `http://127.0.0.1:3000/projects`
- Backend Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/healthz`

部署与环境变量说明见 [docs/local-deployment.md](docs/local-deployment.md)。

## 常用校验

后端：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python backend/scripts/check_architecture.py
.venv/bin/python backend/scripts/check_vocabulary.py
.venv/bin/python backend/scripts/export_frontend_contracts.py --check
```

前端：

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

## 文档导航

推荐阅读顺序：

1. [docs/product-architecture.md](docs/product-architecture.md)
2. [docs/core-data-model.md](docs/core-data-model.md)
3. [docs/module-boundaries.md](docs/module-boundaries.md)
4. [docs/api-contracts.md](docs/api-contracts.md)
5. [docs/fastapi-route-catalog.md](docs/fastapi-route-catalog.md)
6. [docs/implementation-status.md](docs/implementation-status.md)
7. [docs/local-deployment.md](docs/local-deployment.md)

其他文档：

- 术语表：[docs/glossary.md](docs/glossary.md)
- 事件契约：[docs/event-contracts.md](docs/event-contracts.md)
- 事件时序：[docs/event-sequences.md](docs/event-sequences.md)
- Agent 约束：[AGENTS.md](AGENTS.md)

## 当前边界

- PostgreSQL 当前仍是 snapshot adapter，不是最终 row-level repository
- object store 当前仍是本地文件系统路径，不是独立对象存储服务
- Gateway 当前仍由同一个 backend 进程提供本地开发实现
- export 当前仍偏 metadata 级对象流转，不是真实 DOCX / PDF 渲染链
