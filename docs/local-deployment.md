# DR-OS Local Deployment

更新时间：2026-04-05

## 1. 目标

当前仓库支持两类本地运行方式：

- `postgres`：默认推荐主栈，使用 PostgreSQL 持久化开发态 ledger 快照
- `json-legacy`：兼容旧的 JSON ledger 本地模式

两类 profile 都会启动：

- FastAPI Control Plane
- Next.js Research Canvas

其中只有 `postgres` profile 会额外启动真实 PostgreSQL 容器，作为当前本地主链路的默认验证方式。

## 2. 前置条件

本地需要：

- Docker Desktop 或等价 Docker Engine
- Docker Compose v2

建议先复制环境模板：

```bash
cp .env.example .env
```

## 3. 推荐启动方式

### 3.1 PostgreSQL 主栈

在仓库根目录执行：

```bash
docker compose --profile postgres up --build -d
```

查看服务状态：

```bash
docker compose --profile postgres ps
```

该 profile 会启动：

- `postgres`：真实 PostgreSQL 容器，加载 canonical DDL 与开发态 snapshot 表初始化
- `backend`：`DROS_LEDGER_BACKEND=postgres`
- `frontend`：Next.js SSR，通过 Compose service 名访问 backend

### 3.2 Legacy JSON 开发栈

如需保留旧的文件型 durable adapter，可执行：

```bash
docker compose --profile json-legacy up --build -d
```

该 profile 仅用于兼容旧的本地开发方式，不再作为默认推荐。

## 4. 启动后访问

两种 profile 的访问入口保持一致：

- Frontend: `http://127.0.0.1:3000/projects`
- Backend Docs: `http://127.0.0.1:8000/docs`
- Backend Health: `http://127.0.0.1:8000/healthz`

## 5. 国内镜像加速

Compose build 默认支持以下可配置参数，默认值已切到国内镜像：

```text
APT_MIRROR_HOST=mirrors.tuna.tsinghua.edu.cn
PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
NPM_REGISTRY=https://mirrors.tencent.com/npm/
```

如需改回官方源，可在 `.env` 中覆盖这些值。

当前容器文件的额外约定：

- backend 镜像默认以非 root 用户运行，并把本地 object-store 根目录固定到 `/data/object-store`
- frontend 镜像当前使用 Next standalone 多阶段构建，运行时镜像只保留生产所需产物

## 6. 运行时环境约定

### 6.1 Backend

`postgres` profile 中 backend 容器默认接收：

```text
DROS_LEDGER_BACKEND=postgres
DROS_POSTGRES_DSN=postgresql://...
DROS_POSTGRES_SCHEMA=dr_os_dev
DROS_OBJECT_STORE_PATH=/data/object-store
```

同时，`.env.example` 中的以下认证变量已经通过 Compose 透传到 `backend` 和 `backend-json`：

```text
DROS_AUTH_MODE
DROS_AUTH_JWT_SECRET
DROS_AUTH_OIDC_DISCOVERY_URL
DROS_AUTH_JWKS_URL
DROS_AUTH_INTROSPECTION_URL
DROS_AUTH_INTROSPECTION_CLIENT_ID
DROS_AUTH_INTROSPECTION_CLIENT_SECRET
DROS_AUTH_INTROSPECTION_TOKEN_TYPE_HINT
DROS_AUTH_JWT_ALGORITHMS
DROS_AUTH_OIDC_CACHE_TTL_SECONDS
DROS_AUTH_JWKS_CACHE_TTL_SECONDS
DROS_AUTH_JWKS_TIMEOUT_SECONDS
DROS_AUTH_INTROSPECTION_TIMEOUT_SECONDS
DROS_AUTH_JWT_ISSUER
DROS_AUTH_JWT_AUDIENCE
DROS_AUTH_PRINCIPAL_CLAIM
DROS_AUTH_TENANT_CLAIM
DROS_AUTH_PROJECT_ROLE_CLAIM
DROS_AUTH_SCOPES_CLAIM
DROS_AUTH_JTI_CLAIM
DROS_AUTH_REQUIRE_JTI
DROS_AUTH_REVOKED_JTI_LIST
```

说明：

- 当前默认仍是 `DROS_AUTH_MODE=dev_headers`
- 如果切换到 `jwt` 或 `mixed`，需要额外提供合法的 secret / JWKS / OIDC discovery / introspection 配置之一
- Compose 当前只负责把变量传入容器，不代表生产级 IdP 集成已经完成

### 6.2 Frontend

`postgres` profile 中 frontend 容器当前默认接收：

```text
CONTROL_PLANE_BASE_URL=http://backend:8000
NEXT_PUBLIC_CONTROL_PLANE_BASE_URL=http://127.0.0.1:8000
GATEWAY_BASE_URL=http://backend:8000
NEXT_PUBLIC_GATEWAY_BASE_URL=http://127.0.0.1:8000
```

前端配置层当前会按以下顺序回落：

```text
GATEWAY_BASE_URL
NEXT_PUBLIC_GATEWAY_BASE_URL
CONTROL_PLANE_BASE_URL
NEXT_PUBLIC_CONTROL_PLANE_BASE_URL
```

因此，当前本地 Gateway 能力仍由同一个 backend 进程中的开发态实现提供；如果后续拆出独立 Gateway 容器，可直接在 `.env` 中覆盖这两个变量。

补充说明：

- 浏览器侧 realtime 当前经由 frontend 同源 `/api/projects/[projectId]/events` route 转发到 backend SSE，并继续透传 `x-dros-* / request / trace` 头
- 浏览器侧 artifact 下载当前经由 frontend 同源 `/api/projects/[projectId]/artifacts/[artifactId]/download` route 落地；该 route 会在服务端解析 gateway `download-url`，本地 `file://` payload 直接下发附件，外部 URL 则走 `302` 跳转

## 7. 持久化行为

### 7.1 PostgreSQL 主栈

`postgres` profile 当前使用以下命名卷：

- `postgres_data`：持久化 PostgreSQL 数据目录
- `object_store_data`：持久化本地 object-store 文件

说明：

- canonical SQL baseline 会通过 [`ddl_research_ledger_v2.sql`](/Users/musun/dros/sql/ddl_research_ledger_v2.sql) 初始化
- 当前 backend 仍使用 snapshot-based dev ledger adapter，把开发态 ledger 快照持久化到 PostgreSQL
- 这已经替换了 Compose 主链路中的 JSON 文件模式，但还不是最终的 row-level production ledger implementation

### 7.2 Legacy JSON 栈

`json-legacy` profile 当前使用以下命名卷：

- `json_ledger`：持久化 legacy JSON ledger 文件
- `object_store_data`：持久化本地 object-store 文件

关键环境变量为：

```text
DROS_LEDGER_BACKEND=json
DROS_LEDGER_PATH=/data/ledger/ledger.json
DROS_OBJECT_STORE_PATH=/data/object-store
```

## 8. 2026-04-05 已验证结果

2026-04-05 当天已完成一轮运行级验证，本次整理沿用其结果：

- `docker compose --profile postgres up --build -d` 可成功完成构建与启动
- `docker compose --profile postgres ps` 显示 `postgres / backend / frontend` 全部 `healthy`
- `GET /healthz` 返回 `200`
- 已通过 backend 创建 `Compose Stable Smoke Project`
- `GET /v1/projects` 与 `GET /v1/projects/{id}` 可读到新建项目
- Frontend `/projects` 与对应 project detail 页面可 SSR 渲染出新建项目
- 在 Docker Desktop 发生一次重连并重新拉起 Compose 主栈后，API 与前端 SSR 仍能继续读到该项目

补充说明：

- 本次文档整理过程中，`compose.yaml` 又补充了 auth 环境变量透传与 `object_store_data` 卷
- 针对这些变更，已额外执行 `docker compose --profile postgres config` 与 `docker compose --profile json-legacy config`，两类 profile 的配置展开都已通过
- 这些变更之后已重新执行容器级 smoke test；验证过程中 Docker Desktop socket 出现过一次短暂重连，但最终构建、启动、健康检查与 HTTP smoke 都已完成

## 9. 停止与清理

停止 PostgreSQL 主栈：

```bash
docker compose --profile postgres down
```

停止 legacy JSON 栈：

```bash
docker compose --profile json-legacy down
```

连同 PostgreSQL 与 object store 数据卷一起清理：

```bash
docker compose --profile postgres down -v
```

legacy JSON 数据卷清理：

```bash
docker compose --profile json-legacy down -v
```

## 10. 当前边界

当前本地部署文档只代表开发态与 smoke test 口径，不代表生产部署方案：

- PostgreSQL 当前持久化的是 ledger snapshot，不是最终 row-level repository
- object store 当前是本地文件系统路径，不是独立对象存储服务
- Gateway 当前仍由同一个 backend 进程提供本地开发实现，不是独立 BFF / gateway 部署
- export 当前仍偏 metadata 级对象流转，不是真正的 DOCX / PDF 渲染链
- auth 虽已支持 `dev_headers / jwt / mixed` 配置入口，以及 `JWKS / OIDC discovery / introspection / 静态 jti denylist` 这类开发到准生产态门禁，但生产级 IdP 托管 session、可持久化动态 revocation 与更细粒度 RBAC 仍未收口
