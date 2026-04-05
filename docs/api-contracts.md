# DR-OS API Contracts

本文件把产品架构和数据模型收敛成 API 设计约束。详细路由目录以 `docs/fastapi-route-catalog.md` 为准；本文件定义的是统一语义，不是把每个 endpoint 再抄一遍。

如果本文件与 `docs/product-architecture.md` 或 `docs/core-data-model.md` 冲突，以后二者为准。

## 1. 设计约束

1. API 前缀统一为 `/v1`。
2. `tenant_id` 来自鉴权上下文，不允许客户端跨租户指定。
3. project-scoped 授权以有效 scope 为准；有效 scope = `principal scope_tokens ∩ project membership scope_tokens`，不是只看 header / token 自报 role。
4. 所有写接口都以 `project_id` 为业务边界。
5. 创建型 request body 不重复 path-scoped parent ID，例如 `project_id`、`dataset_id`、`manuscript_id`。
6. 所有返回对象使用 `snake_case`。
7. 会触发异步流程的接口必须返回 `workflow_instance_id`、`task_id` 或 `job_id`。
8. API 不暴露任意脚本执行能力。
9. 文稿、证据、分析结果之间的主绑定对象是 `assertion`，不是 `analysis_run`。

## 2. 资源分组

### 2.1 Session / Upload / Realtime

- `GET /v1/session`
- `POST /v1/uploads/sign`
- `POST /v1/uploads/complete`
- `GET /v1/projects/{project_id}/events`
- `GET /v1/projects/{project_id}/artifacts/{artifact_id}/download-url`

语义：

- `uploads/sign` 只发放签名上传地址
- `uploads/complete` 只登记上传完成，不自动创建 analysis run
- 项目级实时事件当前本地开发实现通过 SSE 下发；浏览器侧前端经由同源 `/api/projects/{project_id}/events` proxy 消费，而不是在页面直接拼 backend URL
- 当前本地开发实现中，签名上传地址和 artifact download URL 允许解析到本地 object-store file URL；页面仍只能经由 `GatewayClient` adapter 使用这些能力
- 浏览器侧 artifact 下载当前经由同源 `/api/projects/{project_id}/artifacts/{artifact_id}/download` route 落地；该 route 会先在服务端调用 gateway `download-url`，遇到本地 `file://` 时直接回传附件，否则执行外部跳转
- 当前 auth 支持 `Authorization: Bearer <jwt>`；bearer token 会校验签名、issuer、audience，并把 `principal / tenant / role / scopes` claims 映射为请求上下文
- bearer token 校验来源当前支持 `DROS_AUTH_JWT_SECRET`、`DROS_AUTH_JWKS_URL`、`DROS_AUTH_OIDC_DISCOVERY_URL` 或 `DROS_AUTH_INTROSPECTION_URL`
- 当启用 `DROS_AUTH_OIDC_DISCOVERY_URL` 时，Control Plane 会按 `DROS_AUTH_OIDC_CACHE_TTL_SECONDS` 缓存 provider metadata，并自动解析 `issuer / jwks_uri`
- 当启用 `DROS_AUTH_JWKS_URL` 或 discovery 派生的 `jwks_uri` 时，Control Plane 会按 `DROS_AUTH_JWKS_CACHE_TTL_SECONDS` 复用本地 JWKS cache，并按 `DROS_AUTH_JWKS_TIMEOUT_SECONDS` 控制抓取超时；遇到未知 `kid` 会强制刷新一次后再判定为无效 token
- 当启用 `DROS_AUTH_INTROSPECTION_URL` 时，Control Plane 会向 introspection endpoint 发送 `token` 和可选 `token_type_hint`；响应必须返回 `active=true`，否则请求会被视为 revoked / inactive bearer
- 当前仍保留开发态 header context：`X-Dros-Tenant-Id / X-Dros-Actor-Id / X-Dros-Principal-Id / X-Dros-Project-Role / X-Dros-Scopes / X-Request-Id / X-Trace-Id`
- 当前本地 `SessionRead` 会显式返回 `actor_id / principal_id / tenant_id / scopes_json`
- `DROS_AUTH_MODE=jwt` 时必须携带有效 bearer token；`DROS_AUTH_MODE=mixed` 时优先 bearer，缺失时回退到开发态 header / dev-default principal
- 若启用 `DROS_AUTH_REQUIRE_JTI=true`，token 必须携带 `DROS_AUTH_JTI_CLAIM` 指定的 `jti` claim；`DROS_AUTH_REVOKED_JTI_LIST` 中列出的 token 会被直接拒绝
- project-scoped REST 当前会先校验 tenant / membership，再校验 required scopes；即使 token 自报更高 scope，只要 membership scope 不允许，也会被 `403`
- `GET /projects/{project_id}/events` 当前会在开始 SSE stream 之前先完成 project scope + `events:read` 校验；若 project 不存在或无权访问，会直接返回 HTTP 错误，而不是先写入部分 stream
- `GET /projects/{project_id}/events` 当前会优先输出 schema-backed domain event envelope；`project / dataset_snapshot / workflow / analysis_run / artifact / review / export` 已对齐 `backend/app/schemas/events.py`
- 对尚未建立独立 domain schema 的审计事件，`/events` 当前仍回退到通用 SSE envelope，避免前端监听链路被非核心事件阻断

### 2.2 Projects

- `POST /v1/projects`
- `GET /v1/projects`
- `GET /v1/projects/{project_id}`
- `PATCH /v1/projects/{project_id}`
- `POST /v1/projects/{project_id}/members`
- `GET /v1/projects/{project_id}/members`

主对象：

- `ProjectRead`
- `ProjectMemberRead`

### 2.3 Datasets

- `POST /v1/projects/{project_id}/datasets/import-public`
- `POST /v1/projects/{project_id}/datasets/register-upload`
- `GET /v1/projects/{project_id}/datasets`
- `GET /v1/projects/{project_id}/datasets/{dataset_id}`
- `POST /v1/projects/{project_id}/datasets/{dataset_id}/snapshots`
- `GET /v1/projects/{project_id}/datasets/{dataset_id}/snapshots`
- `POST /v1/projects/{project_id}/datasets/{dataset_id}/policy-checks`

主对象：

- `DatasetRead`
- `DatasetSnapshotRead`

### 2.4 Templates / Workflows / Analysis

- `GET /v1/templates`
- `GET /v1/templates/{template_id}`
- `POST /v1/projects/{project_id}/analysis/plans`
- `POST /v1/projects/{project_id}/workflows`
- `GET /v1/projects/{project_id}/workflows`
- `GET /v1/projects/{project_id}/workflows/{workflow_instance_id}`
- `POST /v1/projects/{project_id}/workflows/{workflow_instance_id}/advance`
- `POST /v1/projects/{project_id}/workflows/{workflow_instance_id}/cancel`
- `POST /v1/projects/{project_id}/analysis-runs`
- `GET /v1/projects/{project_id}/analysis-runs`
- `GET /v1/projects/{project_id}/analysis-runs/{run_id}`

主对象：

- `AnalysisTemplateRead`
- `WorkflowInstanceRead`
- `WorkflowTaskRead`
- `AnalysisRunRead`

关键语义：

- `POST /analysis/plans` 只生成模板建议和参数 JSON，不执行分析
- `POST /workflows` 启动状态机
- `POST /analysis-runs` 负责进入白名单模板执行路径
- `POST /analysis-runs` 当前开发态会经由内置 broker / runner / artifact emitter 立即执行，返回的 `analysis_run.state` 可能已经是 `succeeded` 或 `failed`
- `GET /analysis-runs` 返回 project-scoped analysis run 历史，不要求前端再从 `lineage` 侧聚合
- `GET /analysis-runs/{run_id}` 当前会附带 runner 自动产出的 output artifacts

### 2.5 Artifacts / Assertions / Lineage

- `POST /v1/projects/{project_id}/artifacts`
- `GET /v1/projects/{project_id}/artifacts`
- `GET /v1/projects/{project_id}/artifacts/{artifact_id}`
- `POST /v1/projects/{project_id}/assertions`
- `GET /v1/projects/{project_id}/assertions`
- `GET /v1/projects/{project_id}/assertions/{assertion_id}`
- `POST /v1/projects/{project_id}/lineage-edges`
- `GET /v1/projects/{project_id}/lineage`

主对象：

- `ArtifactRead`
- `AssertionRead`
- `LineageEdgeRead`

关键语义：

- artifact 只登记元数据，不上传二进制文件
- assertion 只追加写，不提供原地覆盖
- assertion 创建后默认进入 `draft`，需要通过 `/verify` 才能进入 `verified`
- lineage edge 主要用于显式登记或回填，不替代核心对象关系；artifact `supersedes` 会同步写入 `artifact.superseded_by`

### 2.6 Evidence

- `POST /v1/projects/{project_id}/evidence/search`
- `POST /v1/projects/{project_id}/evidence/resolve`
- `POST /v1/projects/{project_id}/evidence`
- `GET /v1/projects/{project_id}/evidence`
- `POST /v1/projects/{project_id}/evidence-links`
- `GET /v1/projects/{project_id}/evidence-links`
- `POST /v1/projects/{project_id}/evidence-links/{link_id}/verify`

主对象：

- `EvidenceSourceRead`
- `EvidenceLinkRead`

关键语义：

- `search` 只返回候选，不直接落正式正文
- `resolve` 负责 `PMID / PMCID / DOI` 标准化
- `evidence-links/{link_id}/verify` 会真实回写 `verifier_status`，不是默认固定 `passed`
- `evidence-links` 才是 assertion 与证据绑定的正式入口
- `GET /evidence-links` 返回 project-scoped 绑定历史，不要求前端再从 `assertion detail` 侧聚合

### 2.7 Manuscripts

- `POST /v1/projects/{project_id}/manuscripts`
- `GET /v1/projects/{project_id}/manuscripts`
- `GET /v1/projects/{project_id}/manuscripts/{manuscript_id}`
- `POST /v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks`
- `GET /v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks`
- `POST /v1/projects/{project_id}/manuscripts/{manuscript_id}/versions`
- `POST /v1/projects/{project_id}/manuscripts/{manuscript_id}/render`

主对象：

- `ManuscriptRead`
- `ManuscriptBlockRead`

关键语义：

- block 通过 `block_assertion_links` 引用 assertion
- `render` 只能消费 `assertion.state=verified`

### 2.8 Review / Verification / Export

- `POST /v1/projects/{project_id}/reviews`
- `GET /v1/projects/{project_id}/reviews`
- `POST /v1/projects/{project_id}/reviews/{review_id}/decisions`
- `POST /v1/projects/{project_id}/verify`
- `POST /v1/projects/{project_id}/exports`
- `GET /v1/projects/{project_id}/exports`
- `GET /v1/projects/{project_id}/exports/{export_job_id}`

主对象：

- `ReviewRead`
- `GateEvaluationRead`
- `ExportJobRead`

关键语义：

- `POST /verify` 是导出前强制关卡
- `POST /verify` 当前支持两种校验入口：`target_ids` 或 `manuscript_id`
- `POST /verify` 当前会创建 verification workflow，并把 `gate_evaluations` 持久化到 ledger
- `GET /workflows/{workflow_instance_id}` 可以回读 verification workflow 的 `gate_evaluations`
- `gate_evaluations` 当前由独立 `EvidenceControlPlane` 组件产出，并会逐条写入审计
- `review` 记录人工审批结论
- `review.create / review.decision` 当前会额外落 `review.requested / review.completed`，供 gateway realtime 直接转发
- 当前 export gate 以 `verify` 结果为硬前置，不要求已有 `review` 对象
- `export` 只消费已通过验证的 current manuscript version
- `GET /exports` 返回 project-scoped export job 历史，不要求前端再只依赖 `audit_event + output_artifact` 派生视图
- 成功 `export` 当前会额外落 `export.completed`，供 gateway realtime 推送使用

Evidence 相关补充语义：

- `POST /evidence/search` 当前默认策略是 `project_cache_first`
- `POST /evidence/search` 可通过 `filters.search_scope` 显式声明 `project_cache_first / external_first / project_cache_only / external_only`
- `POST /evidence/search` 的外部多 PMID 抓取当前已走 `EPost + EFetch` batch；默认开发态仍需显式启用 `DROS_NCBI_ENABLED=true`
- `POST /evidence/resolve` 当前在本地未命中时，可通过 opt-in `NCBIAdapter` 外部解析 PMID / PMCID / DOI，并把命中的 evidence source 回写到本地 cache

### 2.9 Audit

- `GET /v1/projects/{project_id}/audit-events`
- `GET /v1/projects/{project_id}/audit-events/{event_id}`
- `POST /v1/internal/audit/replay`

主对象：

- `AuditEventRead`

## 3. 请求 / 响应约束

### 3.1 创建型接口

统一要求：

- 接口幂等时应支持 `Idempotency-Key`
- request body 只包含资源本身所需字段；父级 scope 来自 path 和鉴权上下文
- 返回新对象主键
- 如果触发异步流程，附带 `workflow_instance_id` 或 `job_id`
- 审计型写接口当前会默认把 `request_id / trace_id / principal_id` 从请求上下文带入 `audit_event`

### 3.2 列表型接口

统一要求：

- 支持分页
- 支持按 `state / created_at / type` 过滤
- 默认按 `created_at desc`

### 3.3 异步型接口

统一要求：

- 返回 `accepted` 或对象当前状态
- 由 SSE / WebSocket 或后续查询接口观察进度
- 不在同步请求里阻塞等待长时执行完成

## 4. 与内部模型的映射

| API 资源 | 数据模型主对象 |
| :--- | :--- |
| Project | `projects`, `project_members` |
| Dataset | `datasets`, `dataset_snapshots` |
| Workflow | `workflow_instances`, `workflow_tasks` |
| Analysis | `analysis_templates`, `analysis_runs` |
| Artifact | `artifacts`, `lineage_edges` |
| Evidence | `evidence_sources`, `evidence_chunks`, `evidence_links` |
| Assertion | `assertions` |
| Manuscript | `manuscripts`, `manuscript_blocks`, `block_assertion_links` |
| Review | `reviews` |
| Export | `export_jobs` |
| Audit | `audit_events` |

## 5. 与 Agent 协议的关系

- API 是前端和外部服务的稳定边界。
- Agent JSON Schema 是内部编排边界。
- Research Canvas 只消费 API schema，不消费 Agent schema。
- Workflow Service 负责 API 请求与 Agent 请求之间的字段转换、权限裁剪和状态推进。
- Evidence Control Plane 负责 assertion 绑定、许可证检查和一致性检查，不由前端直连。

## 6. 结论

DR-OS 的 API 不应该暴露“能不能跑一段代码”，而应该暴露：

- 项目和快照怎么创建
- 工作流怎么推进
- artifact 和 assertion 怎么落账
- evidence 怎么绑定和熔断
- review 和 export 怎么完成门禁

这样前端、执行面和 Agent 才能都围绕同一套稳定边界开发。
