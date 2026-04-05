# DR-OS Core Data Model

## 1. 目标

本文件定义 DR-OS 的目标数据模型。重点不是“有哪些表”，而是把平台收敛成一条可计算、可核验、可审计的 lineage。

当前对齐基线：

- 概念设计：本文件
- SQL 基线：`sql/ddl_research_ledger_v2.sql`
- 词表约束：`docs/glossary.md`
- 路由目录：`docs/fastapi-route-catalog.md`
- 事件契约：`docs/event-contracts.md`

统一词表：

- 租户边界：`tenant`, `principal`, `project`
- 数据执行链：`dataset`, `dataset_snapshot`, `workflow_instance`, `workflow_task`, `analysis_run`, `artifact`, `lineage_edge`
- 证据写作链：`evidence_source`, `evidence_chunk`, `assertion`, `evidence_link`, `manuscript`, `manuscript_block`, `block_assertion_link`
- 治理链：`review`, `export_job`, `audit_event`

除以上命名外，不再保留旧对象名作为设计入口。

## 2. 建模原则

1. `Artifact` 是第一公民，不只是附件。
2. `Assertion` 是文稿、证据、统计结果之间的桥。
3. 所有业务对象都必须落到 `tenant_id` 和 `project_id` 边界内。
4. 版本化对象优先新建版本，不原地覆盖。
5. `artifact / assertion / evidence_link / audit_event` 默认 append-only。
6. 文件内容不直接入库，数据库只存 `storage_uri + sha256 + metadata`。
7. 所有用户可见事实必须能追到 `assertion_id`。

## 3. Artifact Lineage DAG

```mermaid
flowchart LR
  DS[Dataset Snapshot] --> AR[Analysis Run]
  AT[Analysis Template] --> AR
  AR --> AF[Artifact]
  AF --> AS[Assertion]
  ES[Evidence Source] --> EL[Evidence Link]
  AS --> EL
  AS --> MB[Manuscript Block]
  MB --> RV[Review]
  MB --> EX[Export Job]
```

## 4. 核心对象分层

### 4.1 租户与权限层

- `tenants`
- `principals`
- `projects`
- `project_members`

### 4.2 数据与执行层

- `datasets`
- `dataset_snapshots`
- `analysis_templates`
- `workflow_instances`
- `workflow_tasks`
- `analysis_runs`
- `artifacts`
- `lineage_edges`

### 4.3 证据与写作层

- `evidence_sources`
- `evidence_chunks`
- `assertions`
- `evidence_links`
- `manuscripts`
- `manuscript_blocks`
- `block_assertion_links`

### 4.4 审核与治理层

- `reviews`
- `export_jobs`
- `audit_events`

## 5. 关键实体

### 5.1 `tenants`

用途：机构或部署租户边界。

关键字段：

- `id`
- `name`
- `tier`
- `deployment_mode`
- `status`

### 5.2 `principals`

用途：用户或服务账号。

关键字段：

- `id`
- `tenant_id`
- `subject_type`
- `external_sub`
- `email`
- `display_name`
- `status`

约束：

- `unique(tenant_id, external_sub)`

### 5.3 `projects`

用途：项目聚合根。

关键字段：

- `id`
- `tenant_id`
- `name`
- `project_type`
- `status`
- `compliance_level`
- `owner_id`
- `active_manuscript_id`

推荐枚举：

- `project_type`: `public_omics`, `clinical_retrospective`, `case_report`, `grant`
- `status`: `draft`, `running`, `review_required`, `approved`, `archived`

### 5.4 `project_members`

用途：项目成员与细粒度权限。

关键字段：

- `project_id`
- `principal_id`
- `role`
- `scopes_json`
- `joined_at`

### 5.5 `datasets`

用途：数据集逻辑对象，不等于快照。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `source_kind`
- `display_name`
- `source_ref`
- `pii_level`
- `license_class`
- `current_snapshot_id`

### 5.6 `dataset_snapshots`

用途：不可变数据快照，是分析运行的直接输入。

关键字段：

- `id`
- `dataset_id`
- `snapshot_no`
- `object_uri`
- `input_hash_sha256`
- `row_count`
- `column_schema_json`
- `deid_status`
- `phi_scan_status`

约束：

- `unique(dataset_id, snapshot_no)`
- `unique(dataset_id, input_hash_sha256)`

### 5.7 `analysis_templates`

用途：白名单模板注册表，对应审核过的 Report Bundle。

关键字段：

- `id`
- `tenant_id nullable`
- `code`
- `version`
- `name`
- `image_digest`
- `script_hash`
- `param_schema_json`
- `output_schema_json`
- `golden_dataset_uri`
- `doc_template_uri`
- `review_status`
- `approved_by`
- `approved_at`

### 5.8 `workflow_instances`

用途：业务状态机实例，是系统主干流程真相源。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `workflow_type`
- `state`
- `current_step`
- `parent_workflow_id`
- `runtime_backend`
- `started_by`

关键约束：

- 只有 `Workflow Service` 能迁移 `state`
- Agent 只能返回建议状态

### 5.9 `workflow_tasks`

用途：工作流步骤粒度状态。

关键字段：

- `id`
- `workflow_instance_id`
- `task_key`
- `task_type`
- `state`
- `assignee_id`
- `input_payload_json`
- `output_payload_json`
- `retry_count`

### 5.10 `analysis_runs`

用途：一次标准化分析执行记录。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `workflow_instance_id`
- `snapshot_id`
- `template_id`
- `state`
- `params_json`
- `param_hash`
- `random_seed`
- `container_image_digest`
- `repro_fingerprint`
- `runtime_manifest_json`
- `input_artifact_manifest_json`
- `job_ref`
- `error_class`
- `error_message_trunc`

`repro_fingerprint` 建议计算：

`sha256(snapshot_hash + template_version + script_hash + param_hash + random_seed + image_digest)`

### 5.11 `artifacts`

用途：图表、表格、json、log、docx、pdf、zip 等统一工件表。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `run_id`
- `artifact_type`
- `storage_uri`
- `mime_type`
- `sha256`
- `size_bytes`
- `metadata_json`
- `superseded_by`

约束：

- `unique(sha256, storage_uri)`
- 不允许原地覆盖

### 5.12 `lineage_edges`

用途：通用血缘边，支撑 lineage explorer。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `from_kind`
- `from_id`
- `edge_type`
- `to_kind`
- `to_id`

推荐边类型：

- `input_of`
- `emits`
- `derives`
- `supersedes`
- `grounds`
- `cited_by`
- `attached_to`
- `reviewed_by`
- `exports`

### 5.13 `evidence_sources`

用途：文献源主表，保存标准化元数据。

关键字段：

- `id`
- `source_type`
- `external_id_norm`
- `doi_norm`
- `title`
- `journal`
- `pub_year`
- `pmid`
- `pmcid`
- `license_class`
- `oa_subset_flag`
- `metadata_json`
- `cached_at`

说明：

- 文献实体以 source 级别去重，不和项目强绑定
- 与项目的关系主要通过 `evidence_links` 和引用行为体现

### 5.14 `evidence_chunks`

用途：检索和 span 定位的 chunk 层。

关键字段：

- `id`
- `evidence_source_id`
- `chunk_no`
- `section_label`
- `text`
- `char_start`
- `char_end`
- `token_count`
- `embedding`
- `lexical_tsv`

实现建议：

- MVP 先放 PostgreSQL + pgvector
- 规模变大后再复制到独立 hybrid retrieval 引擎

### 5.15 `assertions`

用途：系统内“可引用事实”的最小单位。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `assertion_type`
- `text_norm`
- `numeric_payload_json`
- `source_run_id`
- `source_artifact_id`
- `source_span_json`
- `claim_hash`
- `state`
- `supersedes_assertion_id`

推荐枚举：

- `assertion_type`: `background`, `method`, `result`, `limitation`
- `state`: `draft`, `verified`, `blocked`, `stale`

强约束：

- UI 中所有结果句、方法句、背景句都必须能追到 `assertion_id`
- 未绑定 source 的 assertion 不允许进入 approved manuscript block

### 5.16 `evidence_links`

用途：Assertion 与文献证据的绑定。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `assertion_id`
- `evidence_source_id`
- `relation_type`
- `source_chunk_id`
- `source_span_start`
- `source_span_end`
- `excerpt_hash`
- `verifier_status`
- `confidence`

推荐枚举：

- `relation_type`: `supports`, `contradicts`, `method_ref`, `background_ref`

### 5.17 `manuscripts`

用途：稿件聚合对象。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `manuscript_type`
- `title`
- `state`
- `current_version_no`
- `style_profile_json`
- `target_journal`
- `created_by`

### 5.18 `manuscript_blocks`

用途：结构化 block，不等于 assertion。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `manuscript_id`
- `version_no`
- `section_key`
- `block_order`
- `block_type`
- `content_md`
- `status`
- `supersedes_block_id`

### 5.19 `block_assertion_links`

用途：block 与 assertion 的显式多对多映射。

关键字段：

- `block_id`
- `assertion_id`
- `render_role`
- `display_order`

强约束：

- 文稿 block 不直接引用 `analysis_run`
- 所有数值和关键表述必须先通过 assertion 进入 block

### 5.20 `reviews`

用途：审核单对象。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `review_type`
- `target_kind`
- `target_id`
- `state`
- `reviewer_id`
- `checklist_json`
- `comments`
- `decided_at`

### 5.21 `export_jobs`

用途：导出任务。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `manuscript_id`
- `format`
- `state`
- `output_artifact_id`
- `requested_by`
- `requested_at`
- `completed_at`

### 5.22 `audit_events`

用途：append-only 审计日志。

关键字段：

- `id`
- `tenant_id`
- `project_id`
- `actor_id`
- `actor_type`
- `event_type`
- `target_kind`
- `target_id`
- `request_id`
- `trace_id`
- `payload_json`
- `prev_hash`
- `event_hash`

设计要点：

- `prev_hash + event_hash` 形成链式校验
- 关键动作都必须入审计
- 归档层再做 WORM

## 6. 行级安全与追加写

关键表默认要求：

- `ENABLE ROW LEVEL SECURITY`
- `FORCE ROW LEVEL SECURITY`

必须启用的表：

- `projects`
- `project_members`
- `datasets`
- `dataset_snapshots`
- `workflow_instances`
- `workflow_tasks`
- `analysis_runs`
- `artifacts`
- `assertions`
- `evidence_links`
- `manuscripts`
- `manuscript_blocks`
- `reviews`
- `export_jobs`
- `audit_events`

append-only 默认对象：

- `artifacts`
- `assertions`
- `evidence_links`
- `audit_events`

## 7. 结论

DR-OS 的数据模型重点不是“把多少对象存进库”，而是把所有关键对象都纳入同一条可追溯链：

`tenant -> project -> snapshot -> run -> artifact -> assertion -> evidence / manuscript -> review / export -> audit`

只要这条链是稳定的，前端、Agent、模板数量和部署形态都可以渐进增强。
