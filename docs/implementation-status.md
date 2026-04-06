# DR-OS Implementation Status

更新时间：2026-04-06

## 1. 当前结论

当前仓库已经具备一个可验证、可本地联调、可容器化启动的 DR-OS 开发基线，但仍然不是生产可用系统。

截至本次整理，可信结论是：

- 后端当前已实现 `65` 条 `/v1` 路由，外加 `GET /healthz`，合计 `66` 条非文档路由。
- FastAPI Control Plane 已覆盖 `templates / gateway / projects / datasets / workflows / analysis-runs / artifacts / assertions / evidence / evidence-links / manuscripts / reviews / exports / audit replay`。
- 前端当前已具备 `Next.js App Router` 工作区，覆盖 `projects` 列表与 project-scoped 的 `datasets / workflows / analysis-runs / artifacts / assertions / evidence / manuscripts / reviews / exports / audit` 页面。
- 前端服务端数据层与 server action 当前统一走 `createServerControlPlaneClient` / `createServerGatewayClient`，不再直接在 server 侧裸用默认 client。
- 仓库当前支持 `memory / json / postgres` 三种 ledger backend。
- `postgres` backend 当前是开发态 snapshot persistence adapter，用于本地 Compose 主栈，不是最终 row-level PostgreSQL repository。
- 仓库已经提供 `docker compose --profile postgres up --build -d` 的主栈启动方式，并已验证前后端 + PostgreSQL 联调链路。
- 文档入口当前已收口到 `README.md`、`docs/implementation-status.md` 和 `docs/local-deployment.md`；不再继续维护独立的 frontend / backend delivery plan。
- 后端 guardrail 与前端契约检查已在 2026-04-06 重新执行并通过；前端 `lint / typecheck / build / e2e` 与 Compose smoke 最新确认记录见 2026-04-05 条目。

一句话概括当前状态：

`这是一个已经能跑通本地主链路的研发基线，而不是已经完成生产化收口的系统。`

## 2. 当前已实现范围

### 2.1 Backend / Control Plane

当前仓库内已落地的后端模块包括：

- `backend/app/routers/`：`gateway / templates / projects / datasets / workflows / artifacts / assertions / evidence / manuscripts / reviews / exports / audit`
- `backend/app/services/`：对应 bounded context 的 service 实现，以及 `analysis_execution / evidence_control_plane / gateway_service / ncbi_adapter`
- `backend/app/repositories/`：project-scoped repository 基座与各领域 repository
- `backend/app/schemas/`：API、domain、enum、event、agent 结构定义
- `backend/app/object_store.py`：本地 object-store 路径解析、上传对象 key、导出对象 key、artifact 下载路径解析
- `backend/app/settings.py`：ledger backend、object store、auth、NCBI 等配置入口

当前后端已知能力边界：

- `analysis-runs` 已有 project-scoped `create / list / detail`
- `evidence-links` 已有 project-scoped `create / list / verify`
- `evidence chunks` 已有 project-scoped `create / list / detail`
- `exports` 已有 project-scoped `create / list / detail`
- Gateway 本地开发实现已在同一 FastAPI 进程中提供：
  - `GET /v1/session`
  - `POST /v1/uploads/sign`
  - `POST /v1/uploads/complete`
  - `GET /v1/projects/{project_id}/events`
  - `GET /v1/projects/{project_id}/artifacts/{artifact_id}/download-url`
- ledger backend 当前支持：
  - `memory`：默认开发态，进程内存
  - `json`：legacy durable 本地模式
  - `postgres`：开发态快照持久化模式
- object store 当前使用本地文件系统路径，不是独立对象存储服务
- auth 当前在后端代码层已支持 `dev_headers / jwt / mixed`
- bearer token 当前可通过 `DROS_AUTH_JWT_SECRET / DROS_AUTH_JWKS_URL / DROS_AUTH_OIDC_DISCOVERY_URL / DROS_AUTH_INTROSPECTION_URL` 四类入口完成校验
- 启用 introspection 时，Control Plane 当前会要求 `active=true`；既支持 `JWT + introspection` 联合校验，也支持 introspection-only opaque bearer
- project-scoped 授权当前已不是只看 `tenant / membership` 可见性；effective scopes 已按 `principal scope_tokens ∩ project membership scope_tokens` 真正强制执行
- `POST /workflows` 当前已把 `parent_workflow_id` 落成真实 child workflow branch：会校验父 workflow，同步落 `resume_from_parent` task 与 branch 审计，并在 non-terminal parent 上继承 `state / current_step`
- `POST /analysis-runs` 当前已把 `rerun_of_run_id` 落成真实分析重跑链：rerun 仅允许指向同 `snapshot_id + template_id` 的历史 run，新 run 会持久化前序 run 引用，并在 inline artifact emitter 中仅对带显式 `output_slot` 的 output artifact 自动写 `supersedes`
- `Artifact Service` 当前已把 `output_slot` 提升为 artifact 正式字段，并保留对 legacy `metadata_json.output_slot` 的兼容回填：同一 `run_id + artifact_type + output_slot` 不能重复；手工 artifact `supersedes` 也必须满足同 `artifact_type + output_slot`，且 run-backed replacement 必须来自声明了 `rerun_of_run_id` 的新 run
- `POST /manuscripts/{manuscript_id}/versions` 当前已把 `base_version_no` 落成真实版本派生：会从历史版本复制 block 与 `block_assertion_links`，并为新 block 写入 `supersedes_block_id`
- `GET /manuscripts/{manuscript_id}/blocks?version_no=` 当前已能显式读取历史 block 版本；若请求 future `version_no`，返回 `422`
- Gateway `/events` 当前已把 `assertion.created / evidence.linked / evidence.blocked` 接进 schema-backed SSE；evidence link verify 不再只落本地 `evidence.link.verified` 审计别名
- `POST /datasets/{dataset_id}/policy-checks` 当前已把 upload snapshot 的 `pending` 状态收口成显式 `blocking_reasons`，并会在阻断时幂等落 `dataset.snapshot.blocked`，供 dataset gate 与 workspace timeline 直接消费
- NCBI adapter 与 cache 逻辑已在代码中存在，但是否启用仍取决于运行时环境变量

### 2.2 Frontend / Research Canvas

当前前端 App Router 路由已覆盖：

- `/projects`
- `/projects/[projectId]`
- `/projects/[projectId]/datasets`
- `/projects/[projectId]/datasets/[datasetId]`
- `/projects/[projectId]/workflows`
- `/projects/[projectId]/workflows/[workflowInstanceId]`
- `/projects/[projectId]/analysis-runs/[runId]`
- `/projects/[projectId]/artifacts`
- `/projects/[projectId]/artifacts/[artifactId]`
- `/projects/[projectId]/assertions`
- `/projects/[projectId]/assertions/[assertionId]`
- `/projects/[projectId]/evidence`
- `/projects/[projectId]/evidence-links/[linkId]`
- `/projects/[projectId]/manuscripts`
- `/projects/[projectId]/manuscripts/[manuscriptId]`
- `/projects/[projectId]/reviews`
- `/projects/[projectId]/exports`
- `/projects/[projectId]/exports/[exportJobId]`
- `/projects/[projectId]/audit`

同时还存在两个前端 API route：

- `/api/projects/[projectId]/events`
- `/api/projects/[projectId]/artifacts/[artifactId]/download`

当前前端实现形态已经收口为：

- `frontend/features/*/server.ts`：服务端数据读取
- `frontend/features/*/actions.ts`：Server Action
- `frontend/features/*/*.tsx`：资源列表、详情与表单面板
- `frontend/lib/api/control-plane/client.ts`：统一 REST client
- `frontend/lib/api/gateway/`：Gateway adapter 层
- `frontend/lib/api/auth-headers.server.ts`：服务端 header 转发
- `frontend/components/shell/workspace-chrome.tsx`：工作区共享客户端状态容器，统一承接对象链、阶段式 timeline、Inspector 与 realtime 事件选中态
- `frontend/components/shell/project-stage-timeline.tsx`：`project_timeline` 的阶段式主投影组件
- `frontend/features/artifacts/artifact-lineage-graph.tsx`：artifact detail 主画布中的 live lineage adjacency 图
- `frontend/features/exports/export-job-detail.tsx`：export detail route 的 live delivery-chain 页面

当前前端的一个重要实现事实是：

- server data layer 与 server action 现在统一通过 `createServerControlPlaneClient` / `createServerGatewayClient` 注入 header
- 当前自动转发的是 `x-dros-tenant-id / x-dros-actor-id / x-dros-principal-id / x-dros-project-role / x-dros-scopes / x-request-id / x-trace-id` 开发态上下文头
- 这不等于浏览器端已经形成完整 bearer token / session 的端到端托管链路
- `GatewayClient` 在未显式设置网关 base URL 时，会自动回落到 Control Plane base URL
- 浏览器侧 realtime 当前经由 Next 同源 `/api/projects/[projectId]/events` route proxy 到 backend SSE；如果上游在开始流之前返回 `403 / 404`，同源 route 会先原样透传错误，再决定是否开始流式响应
- artifact 下载当前经由 Next 同源 `/api/projects/[projectId]/artifacts/[artifactId]/download` route 调用 gateway `download-url`；若返回本地 `file://` 则由 Node route 直接回传附件，否则再做 `302` 跳转
- project workspace 当前已经改成三栏工作区：对象链导航、阶段式 `project_timeline` 主投影、主画布和独立 Inspector
- `project_timeline` 当前已不再是简单事件列表，而是由 `workflow / analysis_run / artifact / assertion / evidence / review / export` 与 live events 联合投影出的 6 段阶段 timeline
- workspace 在收到会改变 ledger 投影的 SSE 后，当前会主动 refresh server projection；live event feed、stage cards 和 route-object inspector 不再长期停留在首屏 SSR 快照
- `InspectorPanel` 当前既能承接阶段焦点，也能承接具体事件焦点；事件焦点会展示 `trace / request / payload` 与 `workflow / analysis-run / artifact / audit` 跳转
- project detail route 当前还会把 Inspector 默认切到当前 canonical object；`workflow / analysis-run / artifact / assertion / manuscript / export_job` 详情页会展示 upstream / grounding / consumer 邻接跳转，而不是只显示静态摘要
- artifact detail 主画布当前已经不是静态 metadata 卡片：live lineage graph 会展示 upstream / grounding / consumer 三栏邻接；对导出产物，graph 与 Inspector 都会经由 `export_job` 反解回 source manuscript
- `Review Gate` 当前已按 active manuscript 的 current version window 收口；旧 review 不再持续污染新 version 的工作区阶段状态
- 移动端在 Inspector 收起后，切换阶段或选中新事件都会自动展开该面板
- 浏览器侧 live detail 组件当前不会再直接 import 带 `server-only` 依赖的 server client；`workflow` / `manuscript` detail 的增量刷新改为浏览器侧定向 `fetch`，避免 Next build 把 server-only 模块卷入 client bundle
- `evidence_link` 当前已产品化为独立 detail route（`/evidence-links/[linkId]`），Inspector 把 `evidenceLink` 视为 canonical route object 并展示 upstream assertion / evidence source / consumer manuscript 邻接
- `evidence_link` detail 当前会优先消费 persisted `source_chunk`，并在缺失 chunk 时才回落到 `evidence_source.metadata_json` preview；主画布会显示 chunk 元数据和高亮片段，workspace Inspector 也会把 quoted span / source preview 带入当前对象摘要，而不是只显示 span 坐标 JSON
- evidence dashboard 当前每条 evidence link 都可以直接跳转到独立 detail 页面；assertion focus Inspector 也会把 evidence links 按条目展示而非只显示 registry 汇总
- artifact lineage graph 当前支持 `figure/table → result_json` 图谱浏览：`derives` edge 反向追溯到 parent result_json，grounding 栏合并展示 direct + inherited assertions 以及逐条 evidence link；result_json 详情页也会在 consumers 栏展示 derived figure/table children

### 2.3 Local Deployment / Compose

当前本地部署入口有两个 profile：

- `postgres`：默认推荐主栈
- `json-legacy`：兼容旧的 JSON ledger 本地模式

当前 `postgres` profile 由以下服务组成：

- `postgres`
- `backend`
- `frontend`

当前 Compose 已具备以下事实：

- Docker build 默认支持国内镜像加速：
  - `APT_MIRROR_HOST=mirrors.tuna.tsinghua.edu.cn`
  - `PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple`
  - `NPM_REGISTRY=https://mirrors.tencent.com/npm/`
- 容器打包当前已收口为：
  - backend 镜像非 root 运行，默认把 object-store 根目录指向 `/data/object-store`
  - frontend 镜像使用 Next standalone 多阶段构建，运行时仅保留生产所需产物
- 后端容器默认使用：
  - `DROS_LEDGER_BACKEND=postgres`
  - `DROS_POSTGRES_DSN=postgresql://...`
  - `DROS_POSTGRES_SCHEMA=dr_os_dev`
- 前端容器使用：
  - `CONTROL_PLANE_BASE_URL=http://backend:8000`
  - `NEXT_PUBLIC_CONTROL_PLANE_BASE_URL=http://127.0.0.1:8000`
- `GATEWAY_BASE_URL` / `NEXT_PUBLIC_GATEWAY_BASE_URL` 当前也已在 Compose 中显式设置，默认仍指向同一个 backend 进程
- Compose 当前不会启动单独 Gateway 容器；Gateway 能力由 backend 进程内的本地开发实现提供
- Compose 当前已为 PostgreSQL 和本地 object store 配置命名卷
- `.env.example` 中的 auth 变量当前已可通过 Compose 注入 backend / backend-json 容器

需要特别说明的边界：

- PostgreSQL 当前持久化的是 ledger 快照，不是按 canonical DDL 直接运行全部业务 repository
- canonical DDL 已通过 `sql/ddl_research_ledger_v2.sql` 在数据库中初始化，但当前业务读写主路径仍是开发态快照适配层
- 这意味着“数据库结构已初始化”和“业务仓储已完全切换到 row-level PostgreSQL”是两件不同的事，后者尚未完成

## 3. 最新验证记录

### 3.1 Backend / Guardrails（2026-04-06）

本次整理时重新执行并确认通过的命令包括：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python backend/scripts/check_architecture.py
.venv/bin/python backend/scripts/check_vocabulary.py
.venv/bin/python backend/scripts/export_frontend_contracts.py --check
```

结果：

- `pytest`: `56 passed`
- `check_architecture`: passed
- `check_vocabulary`: passed
- `export_frontend_contracts --check`: passed

### 3.2 Frontend（最新确认：2026-04-06）

```bash
cd frontend && npm run test
cd frontend && npm run lint
cd frontend && npm run typecheck
cd frontend && npm run build
cd frontend && npm run test:e2e
```

结果：

- `test`: passed
- `lint`: passed
- `typecheck`: passed
- `build`: passed
- `test:e2e`: `10 passed, 10 skipped`

补充说明：

- `typecheck` 当前已改为 `next typegen + tsc --noEmit --incremental false`
- 这样可以避免 `.next/types` 残留状态导致的假失败
- 本轮新增 E2E 已覆盖 export detail route、artifact lineage graph live adjacency、以及 export output artifact 到 manuscript upstream 的回链

### 3.3 Compose Smoke Test（最新确认：2026-04-05）

2026-04-05 当天已完成一次运行级 smoke test，验证命令为：

```bash
docker compose --profile postgres up --build -d
docker compose --profile postgres ps
```

运行级结果：

- `postgres / backend / frontend` 三个服务均为 `healthy`
- 后端健康检查 `GET /healthz` 返回 `200`
- 已通过后端创建 `Compose Stable Smoke Project`
- `GET /v1/projects` 与 `GET /v1/projects/{id}` 可读到新建项目
- 前端 `/projects` 与对应 project detail 页面可 SSR 渲染出新建项目
- 在 Docker Desktop 发生一次重连并重新拉起 Compose 主栈后，API 与前端 SSR 仍能继续读到该项目

补充说明：

- 本次文档整理过程中，`compose.yaml` 又新增了 auth 环境变量透传与 `object_store_data` 卷
- 针对这部分变更，已额外执行 `docker compose --profile postgres config` 与 `docker compose --profile json-legacy config`，并确认两类 profile 的配置都可正常展开
- 容器级 smoke test 已在这些变更之后重新执行；验证过程中 Docker Desktop socket 存在过一次短暂重连，但最终 `up --build -d`、健康检查与 HTTP smoke 均已完成

## 4. 当前文档化边界

为了避免把“代码里有文件”误写成“系统已完全实现”，当前状态文档采用以下口径：

- `README.md`：仓库入口、上手路径、文档导航
- `docs/implementation-status.md`：当前代码已经落地的真实事实
- `docs/local-deployment.md`：本地部署、Compose、环境变量和验证口径
- `已实现`：本次已直接从代码、命令输出或运行结果确认
- `已接入`：当前代码路径中已存在真实调用或真实路由
- `存在实现`：代码文件存在，但本次未单独做业务级完整验证
- `未完成`：仍属于后续工作，不应在对外口径中视为已上线能力

## 5. 当前未完成项

以下内容仍不应被误判为“已完成”：

- row-level PostgreSQL repository 与真正的 canonical ledger 读写切换
- 独立 Object Storage 服务与生产级 artifact 生命周期管理
- 独立 Gateway / BFF 部署与浏览器侧完整 session / bearer relay
- 外部 IdP 托管 session、可持久化动态 revocation、以及正式 principal directory / 细粒度 RBAC 收口
- rootless / 断网 / run-to-completion 的远程执行面
- 真正的 DOCX / PDF 渲染链，而不是 metadata 级导出对象
- 生产级 RLS、审计归档、搜索索引与外部系统集成
- `evidence_link` detail route、`evidence_chunk` create/list/detail、inline source preview、span highlighting 与 `figure/table -> result_json -> assertion -> evidence -> manuscript block` 主图谱浏览已产品化；剩余缺口收敛为多 chunk source 的更完整浏览面、chunk 级独立 detail route，以及真正来自外部 ingest / parser 的 chunk provenance，而不是只靠 source upsert 时的 inline preview materialization
- `discussion mode / analysis_planning` 还没有形成面向用户的完整产品化前置流程

## 6. 目前最准确的工程判断

如果从工程推进角度总结当前仓库：

- 可以做：前后端联调、契约校验、本地主链路演示、容器化 smoke test
- 不应该做：把当前 Compose 主栈当成生产部署方案
- 下一阶段最有价值的工作：
  - 把 PostgreSQL 从 snapshot adapter 推进到真正的 row-level repository
  - 把 object store / auth / gateway 的运行时边界继续收口
  - 在 CI 中加入 `docker compose --profile postgres up --build` 或等价构建检查
