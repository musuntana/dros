# DR-OS FastAPI Route Catalog

本文件是面向工程拆分的 route 清单，默认对应：

- BFF / Gateway 负责 session、SSE/WebSocket、signed URL。
- FastAPI Control Plane 负责稳定 REST API、状态推进和权限裁剪。
- 长流程通过 workflow runtime 推进，API 不直接承载长任务执行。

本文件只定义路由目录和 owner，不重复定义领域模型。若与 `docs/product-architecture.md` 或 `docs/core-data-model.md` 冲突，以后二者为准。

## 0. 当前仓库实现快照

截至 2026-04-05，当前代码库的边界是：

- 仓库内已实现 `docs/fastapi-route-catalog.md` 中全部 61 条业务 / 内部 REST 路由。
- 仓库内额外实现了 1 条系统路由：`GET /healthz`。
- assertion 当前创建后默认进入 `draft`，需要先经过 `/v1/projects/{project_id}/verify` 才能进入 `verified` 消费态。
- export 当前要求当前 manuscript version 已存在正式 verify 结果；未 verify 的稿件版本会被阻断。
- `/verify` 当前会创建真实 verification workflow，并把 `gate_evaluations` 写入 ledger；workflow detail 可回读该次 gate 结果。
- `Citation Resolver / Claim-Evidence Binder / Data Consistency Checker / License Guard` 当前已具备 MVP 规则实现，并已抽出为独立 `EvidenceControlPlane` 组件。
- `analysis_run` 当前已接入开发态 `InMemory JobBroker + deterministic inline Runner + inline Artifact Emitter`，成功执行时会自动落 `result_json / table / figure / manifest / log` artifact。
- `evidence-links/{link_id}/verify` 当前会真实回写 `verifier_status`，不再默认直接 `passed`。
- `lineage-edges` 当前已能把 artifact `supersedes` 关系写入 `artifact.superseded_by`，供 broken chain 校验消费。
- dangling assertion 当前已能在 manuscript verify 时被真实拦截；gate 结果会逐条写入审计。
- `evidence/search` 当前默认策略仍是 `project_cache_first`，但已支持通过 `filters.search_scope` 显式切换到 `external_first / project_cache_only / external_only`。
- `evidence/resolve` 当前已可在本地未命中时，通过 opt-in `NCBIAdapter` 外部解析 PMID / PMCID / DOI，并把结果回写到本地 evidence source cache。
- 多 PMID 外部抓取当前已通过 `NCBIAdapter` 接入 `EPost + EFetch` batch。
- repository 基座当前已支持 `memory / json / postgres` 三种 ledger backend。
- `json` backend 仍用于 legacy 本地 durable 模式；`postgres` 当前用于 Compose 主栈的开发态 snapshot persistence，不是最终 row-level PostgreSQL repository。
- Gateway owner 的 5 条路由当前已在仓库内落地为本地开发实现：
  - `/v1/session`
  - `/v1/uploads/sign`
  - `/v1/uploads/complete`
  - `/v1/projects/{project_id}/events`
  - `/v1/projects/{project_id}/artifacts/{artifact_id}/download-url`
- request-scoped auth context 当前已支持通过 `Authorization: Bearer <jwt>` 或开发态 header 注入；project list/detail 与 project-scoped object detail 已按 tenant / membership 收口。
- `DROS_AUTH_OIDC_DISCOVERY_URL` 当前已可自动解析 `issuer / jwks_uri`，并具备本地 discovery metadata cache。
- `DROS_AUTH_JWKS_URL` 与 discovery 派生 `jwks_uri` 当前都已具备本地 JWKS cache 与 `kid` 轮换刷新逻辑；同一 keyset 在 TTL 内复用，未知 `kid` 会触发一次强制拉新。
- `DROS_AUTH_INTROSPECTION_URL` 当前已接入 bearer introspection；既支持 opaque token，也支持在本地 JWT 校验后继续做 `active` gate。
- bearer token 当前已支持最小 `jti` lifecycle gate：可强制 `jti` claim，并按静态 denylist 拒绝已撤销 token。
- global scopes 与 project-scoped required scopes 当前都已正式执行；project effective scopes 以 `principal scope_tokens ∩ membership scope_tokens` 为准。
- `/v1/projects/{project_id}/events` 当前会优先输出 schema-backed domain event envelope；`project / dataset_snapshot / workflow / analysis_run / artifact / review / export` 已接上结构化序列化，其余审计事件仍走通用 SSE envelope 回退。
- 当前开发态 `uploads/sign` 与 `download-url` 会返回本地 object-store file URL；前端仍必须继续通过 `GatewayClient` adapter 消费这些能力，而不是把 URL 规则写死进业务页面。

## 1. 约定

- API 前缀统一为 `/v1`.
- 所有写接口都要求 `tenant_id` 和 `project_id` 落在鉴权上下文，不允许客户端跨租户指定。
- 创建型 request body 不重复 path-scoped parent ID，例如 `project_id`、`dataset_id`、`manuscript_id`。
- 所有会触发工作流或异步执行的写接口，响应里都返回 `workflow_instance_id`、`task_id` 或 `job_id`。
- `analysis_runs`、`artifacts`、`assertions`、`evidence_links`、`audit_events` 不暴露“原地覆盖”语义。
- SSE 用于长任务进度、review 状态和 artifact 预览刷新；正式对象查询仍走 REST。

## 2. Session / Realtime / Upload

说明：

- 本节路由由 Gateway owner 持有，当前代码仓库已提供本地开发实现。
- `/events` 当前是 project-scoped SSE；核心业务事件按 schema 推送，非 schema 审计事件按通用 envelope 回退。
- `/events` 当前会在 `StreamingResponse` 开始前先完成 project scope + `events:read` 校验；若 project 不存在或无权访问，直接返回 HTTP 错误，不返回半截 SSE。
- 当前仓库的 auth 已支持 JWT bearer + OIDC discovery + JWKS cache/rotation + token introspection + `jti` denylist 校验；同时保留 `mixed / dev_headers` 开发态回退，不等同于最终生产 IdP 托管 session。
- 浏览器侧当前经由同源 `/api/projects/[projectId]/events` 与 `/api/projects/[projectId]/artifacts/[artifactId]/download` route 消费 Gateway 能力；业务页面不直接处理 backend `file://` signed URL。

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/v1/session` | Gateway | 返回当前 actor / principal / tenant / role scopes | `SessionRead` |
| `POST` | `/v1/uploads/sign` | Gateway + Dataset Service | 生成对象存储签名上传 URL | `SignedUploadResponse` |
| `POST` | `/v1/uploads/complete` | Gateway + Dataset Service | 回调上传完成，登记临时文件引用 | `UploadCompleteResponse` |
| `GET` | `/v1/projects/{project_id}/events` | Gateway | SSE 订阅项目级 workflow/review/export 事件 | `text/event-stream` |
| `GET` | `/v1/projects/{project_id}/artifacts/{artifact_id}/download-url` | Gateway | 生成 artifact 临时下载地址 | `SignedArtifactUrlResponse` |

## 3. Projects

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/v1/projects` | Project Service | 创建项目 | `CreateProjectResponse` |
| `GET` | `/v1/projects` | Project Service | 分页列项目 | `ProjectListResponse` |
| `GET` | `/v1/projects/{project_id}` | Project Service | 查询项目详情和概览计数 | `ProjectDetailResponse` |
| `PATCH` | `/v1/projects/{project_id}` | Project Service | 更新名称、状态、active manuscript 指针 | `ProjectDetailResponse` |
| `POST` | `/v1/projects/{project_id}/members` | Project Service | 添加项目成员 | `AddProjectMemberResponse` |
| `GET` | `/v1/projects/{project_id}/members` | Project Service | 查询成员与 scopes | `ProjectMemberListResponse` |

建议模型：

- `CreateProjectRequest`: `name`, `project_type`, `compliance_level`, `owner_id`, `target_journal?`
- `ProjectDetailResponse`: `project`, `active_workflows`, `latest_snapshot`, `active_manuscript`, `review_summary`

## 4. Datasets

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/v1/projects/{project_id}/datasets/import-public` | Dataset Service | 从 GEO / TCGA / SEER 导入公共数据集 | `CreateDatasetResponse` |
| `POST` | `/v1/projects/{project_id}/datasets/register-upload` | Dataset Service | 把已上传文件登记为 dataset | `CreateDatasetResponse` |
| `GET` | `/v1/projects/{project_id}/datasets` | Dataset Service | 列出项目数据集 | `DatasetListResponse` |
| `GET` | `/v1/projects/{project_id}/datasets/{dataset_id}` | Dataset Service | 查询数据集与当前快照 | `DatasetDetailResponse` |
| `POST` | `/v1/projects/{project_id}/datasets/{dataset_id}/snapshots` | Dataset Service | 创建不可变 snapshot，计算 hash 和 schema scan | `CreateDatasetSnapshotResponse` |
| `GET` | `/v1/projects/{project_id}/datasets/{dataset_id}/snapshots` | Dataset Service | 列出历史 snapshot | `DatasetSnapshotListResponse` |
| `POST` | `/v1/projects/{project_id}/datasets/{dataset_id}/policy-checks` | Review & Policy | 执行 PII / deid / license 预检查 | `DatasetPolicyCheckResponse` |

边界：

- `import-public` 只做注册和抓取，不直接启动统计分析。
- `register-upload` 默认进入 `phi_scan_status=pending`，由策略服务决定能否启动后续 workflow。
- `snapshot` 对象一旦创建不可修改，只能产生新的 `snapshot_no`.

## 5. Workflows / Analysis / Templates

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/v1/templates` | Template Registry | 列出白名单模板 | `TemplateListResponse` |
| `GET` | `/v1/templates/{template_id}` | Template Registry | 查询模板详情、schema、golden dataset | `TemplateDetailResponse` |
| `POST` | `/v1/projects/{project_id}/analysis/plans` | Workflow + Analysis Agent | 生成模板建议和参数 JSON，不执行 | `CreateAnalysisPlanResponse` |
| `POST` | `/v1/projects/{project_id}/workflows` | Workflow Service | 启动标准 workflow | `CreateWorkflowResponse` |
| `GET` | `/v1/projects/{project_id}/workflows` | Workflow Service | 分页列工作流实例 | `WorkflowListResponse` |
| `GET` | `/v1/projects/{project_id}/workflows/{workflow_instance_id}` | Workflow Service | 查询状态机、步骤、gate 结果 | `WorkflowDetailResponse` |
| `POST` | `/v1/projects/{project_id}/workflows/{workflow_instance_id}/advance` | Workflow Service | 系统或人工推进下一步 | `WorkflowDetailResponse` |
| `POST` | `/v1/projects/{project_id}/workflows/{workflow_instance_id}/cancel` | Workflow Service | 取消 workflow | `WorkflowDetailResponse` |
| `POST` | `/v1/projects/{project_id}/analysis-runs` | Workflow + Job Broker | 创建 analysis run 并进入开发态执行链 | `CreateAnalysisRunResponse` |
| `GET` | `/v1/projects/{project_id}/analysis-runs` | Workflow + Job Broker | 分页列出 project 下的 analysis run | `AnalysisRunListResponse` |
| `GET` | `/v1/projects/{project_id}/analysis-runs/{run_id}` | Workflow + Artifact Service | 查询 analysis run 元数据与输出 artifact | `AnalysisRunDetailResponse` |

建议把 `POST /workflows` 的 `workflow_type` 限定成：

- `public_dataset_standard_analysis`
- `clinical_retrospective_analysis`
- `evidence_backfill`
- `manuscript_verification`
- `export_pipeline`

## 6. Artifacts / Assertions / Lineage

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/v1/projects/{project_id}/artifacts` | Artifact Service | 注册 artifact 元数据 | `CreateArtifactResponse` |
| `GET` | `/v1/projects/{project_id}/artifacts` | Artifact Service | 按 run/type 列表查询 | `ArtifactListResponse` |
| `GET` | `/v1/projects/{project_id}/artifacts/{artifact_id}` | Artifact Service | 查询 artifact 元数据 | `ArtifactDetailResponse` |
| `POST` | `/v1/projects/{project_id}/assertions` | Manuscript Service | 创建 assertion | `CreateAssertionResponse` |
| `GET` | `/v1/projects/{project_id}/assertions` | Manuscript Service | 按 state/source 查询 assertion | `AssertionListResponse` |
| `GET` | `/v1/projects/{project_id}/assertions/{assertion_id}` | Manuscript Service | 查询 assertion 和证据绑定 | `AssertionDetailResponse` |
| `POST` | `/v1/projects/{project_id}/lineage-edges` | Artifact Service | 显式登记 lineage edge | `CreateLineageEdgeResponse` |
| `GET` | `/v1/projects/{project_id}/lineage` | Artifact Service | 查询 lineage explorer 视图 | `LineageQueryResponse` |

边界：

- `assertions` 只创建新版本，不提供 `PUT`.
- assertion 创建后默认先进入 `draft`，不能直接当作 `verified` 事实消费。
- `artifacts` 只登记对象存储定位和哈希，不上传二进制内容。
- `lineage-edges` 主要用于回填和显式修复，不替代核心对象关系；其中 artifact `supersedes` 会同步写入 `artifact.superseded_by`。

## 7. Evidence / Citation Resolver

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/v1/projects/{project_id}/evidence/search` | Evidence Service | PubMed/PMC 结构化检索 + rerank | `EvidenceSearchResponse` |
| `POST` | `/v1/projects/{project_id}/evidence/resolve` | Evidence Service | 标准化 PMID / PMCID / DOI | `ResolveEvidenceResponse` |
| `POST` | `/v1/projects/{project_id}/evidence` | Evidence Service | 将候选结果写入 evidence source cache / project binding | `UpsertEvidenceSourceResponse` |
| `GET` | `/v1/projects/{project_id}/evidence` | Evidence Service | 查询与项目相关的 evidence links / source refs | `EvidenceSourceListResponse` |
| `POST` | `/v1/projects/{project_id}/evidence-links` | Evidence Service | 将 assertion 绑定到 evidence source/span | `CreateEvidenceLinkResponse` |
| `GET` | `/v1/projects/{project_id}/evidence-links` | Evidence Service | 分页列出 project 下的 evidence link | `EvidenceLinkListResponse` |
| `POST` | `/v1/projects/{project_id}/evidence-links/{link_id}/verify` | Review + Verifier | 对 span / 语义边界重新核验 | `VerifyEvidenceLinkResponse` |

实现注意：

- `search` 只返回候选，不直接把自由文本结论写入文稿。
- `resolve` 必须遵守 `NCBI E-utilities` 限速：无 key `<=3 req/s`，有 key `<=10 req/s`。
- 全文自动化抓取只面向 `PMC Open Access Subset` 或其他明确许可来源；非 OA 默认 `metadata_only`.
- `evidence-links/{link_id}/verify` 当前会对 identifier / license 边界做真实校验，不再是占位通过。
- 当前外部 NCBI 路径仍是 opt-in 开关，不是默认强依赖；多 PMID 的 `EPost + EFetch` batch 已落地，但默认检索策略仍不是 external-first。

## 8. Manuscripts

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/v1/projects/{project_id}/manuscripts` | Manuscript Service | 创建稿件对象 | `CreateManuscriptResponse` |
| `GET` | `/v1/projects/{project_id}/manuscripts` | Manuscript Service | 列出稿件 | `ManuscriptListResponse` |
| `GET` | `/v1/projects/{project_id}/manuscripts/{manuscript_id}` | Manuscript Service | 查询稿件当前版本 | `ManuscriptDetailResponse` |
| `POST` | `/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks` | Manuscript Service | 追加新 block | `CreateManuscriptBlockResponse` |
| `GET` | `/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks` | Manuscript Service | 查询指定版本 blocks | `ManuscriptBlockListResponse` |
| `POST` | `/v1/projects/{project_id}/manuscripts/{manuscript_id}/versions` | Manuscript Service | 冻结当前 block 集合为新版本 | `CreateManuscriptVersionResponse` |
| `POST` | `/v1/projects/{project_id}/manuscripts/{manuscript_id}/render` | Manuscript Service | 基于 verified assertions 渲染结构化初稿 | `RenderManuscriptResponse` |

边界：

- block 内容必须能回链到 `assertion_id`.
- `render` 只能消费 `assertion.state=verified`.
- block 更新通过“创建 superseding block + bump version”，不做原地改写。

## 9. Review / Policy / Export

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/v1/projects/{project_id}/reviews` | Review Service | 创建审核单 | `CreateReviewResponse` |
| `GET` | `/v1/projects/{project_id}/reviews` | Review Service | 列出审核单 | `ReviewListResponse` |
| `POST` | `/v1/projects/{project_id}/reviews/{review_id}/decisions` | Review Service | approve / reject / request changes | `ReviewDecisionResponse` |
| `POST` | `/v1/projects/{project_id}/verify` | Review + Evidence Control Plane | 运行导出前全链路核验 | `RunVerificationResponse` |
| `POST` | `/v1/projects/{project_id}/exports` | Export Service | 创建导出任务 | `CreateExportJobResponse` |
| `GET` | `/v1/projects/{project_id}/exports` | Export Service | 分页列出 project 下的 export job | `ExportJobListResponse` |
| `GET` | `/v1/projects/{project_id}/exports/{export_job_id}` | Export Service | 查询导出状态和输出 artifact | `ExportJobDetailResponse` |

建议把 `POST /verify` 的返回统一成三层：

- `gate_evaluations`
- `verifier_result`
- `blocking_summary`

当前代码中的落地语义：

- `/verify` 当前支持两种入口：按 `target_ids` 校验对象，或按 `manuscript_id` 校验当前稿件版本。
- `/verify` 当前会返回可查询的 `workflow_instance_id`；后续可通过 `GET /workflows/{workflow_instance_id}` 回读对应 `gate_evaluations`。
- `review` 当前负责治理记录和人工决策审计；export 的技术门禁仍以正式 verify 结果为准，不以 `review` 对象存在与否作为硬前置。
- `POST /exports` 当前只接受已经完成正式 verify 的 current manuscript version；否则返回 `blocked` export job。

## 10. Audit / Admin

| Method | Path | Owner | Purpose | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/v1/projects/{project_id}/audit-events` | Audit Service | 分页查询 append-only 审计日志 | `AuditEventListResponse` |
| `GET` | `/v1/projects/{project_id}/audit-events/{event_id}` | Audit Service | 查询单条审计记录和链式 hash | `AuditEventDetailResponse` |
| `POST` | `/v1/internal/audit/replay` | Audit Service | 内部工具，校验 hash chain | `AuditReplayResponse` |

## 11. 建议的 Pydantic 模块拆分

- `backend/app/schemas/api_projects.py`
- `backend/app/schemas/api_datasets.py`
- `backend/app/schemas/api_workflows.py`
- `backend/app/schemas/api_evidence.py`
- `backend/app/schemas/api_manuscripts.py`
- `backend/app/schemas/api_reviews.py`
- `backend/app/schemas/api_exports.py`
- `backend/app/schemas/events.py`

这样做的原因：

- 现有 `api.py` 已经开始变成单文件聚合，不适合继续承载 workflow、upload、review、export 的扩展。
- route catalog 与 schema 模块一一对应后，FastAPI router 可以按 bounded context 直接拆分。
