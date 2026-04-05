# DR-OS Event Contracts

本文件是 `contracts/events/*.schema.json` 的阅读索引。规范本身以 JSON Schema 为准，这里只回答三个问题：

- 每条事件的 envelope 长什么样
- producer / consumer 该用什么幂等键
- 哪些事件属于 MVP 主链路

本文件不再维护旧事件名兼容表。事件命名以当前 schema 和 `docs/event-sequences.md` 为准。

## 1. 统一 Envelope

所有领域事件都使用同一个 envelope 形态：

```json
{
  "event_id": "uuid",
  "event_name": "analysis.run.succeeded",
  "schema_version": "1.0.0",
  "produced_by": "runner",
  "trace_id": "trace_123",
  "request_id": "req_123",
  "tenant_id": "uuid",
  "project_id": "uuid",
  "idempotency_key": "analysis_run_id",
  "occurred_at": "2026-04-03T12:00:00Z",
  "payload": {}
}
```

固定约束：

- `tenant_id`、`project_id`、`trace_id` 必填。
- `idempotency_key` 必填，consumer 不应自行猜测去重规则。
- `payload` 必须符合对应 schema 文件。

## 2. 核心事件

| Event | Schema File | Producer | 推荐幂等键 |
| :--- | :--- | :--- | :--- |
| `project.created` | `contracts/events/project-created.schema.json` | Project Service | `project_id` |
| `dataset.snapshot.created` | `contracts/events/dataset-snapshot-created.schema.json` | Dataset Service | `snapshot_id` |
| `dataset.snapshot.blocked` | `contracts/events/dataset-snapshot-blocked.schema.json` | Review & Policy | `snapshot_id + reason` |
| `workflow.started` | `contracts/events/workflow-started.schema.json` | Workflow Service | `workflow_instance_id` |
| `analysis.run.requested` | `contracts/events/analysis-run-requested.schema.json` | Workflow Service | `analysis_run_id` |
| `analysis.run.succeeded` | `contracts/events/analysis-run-succeeded.schema.json` | Runner | `analysis_run_id` |
| `analysis.run.failed` | `contracts/events/analysis-run-failed.schema.json` | Runner | `analysis_run_id + exit_code` |
| `artifact.created` | `contracts/events/artifact-created.schema.json` | Artifact Service | `artifact_id` |
| `assertion.created` | `contracts/events/assertion-created.schema.json` | Manuscript Service | `assertion_id` |
| `evidence.linked` | `contracts/events/evidence-linked.schema.json` | Evidence Service | `assertion_id + evidence_source_id` |
| `evidence.blocked` | `contracts/events/evidence-blocked.schema.json` | Evidence Service | `assertion_id + reason` |
| `review.requested` | `contracts/events/review-requested.schema.json` | Manuscript / Policy | `review_id` |
| `review.completed` | `contracts/events/review-completed.schema.json` | Review Service | `review_id` |
| `export.completed` | `contracts/events/export-completed.schema.json` | Export Service | `export_job_id` |

## 3. MVP 必接事件

如果只做 MVP 主链路，建议 producer / consumer 先接这 8 条：

- `project.created`
- `dataset.snapshot.created`
- `workflow.started`
- `analysis.run.requested`
- `analysis.run.succeeded`
- `artifact.created`
- `assertion.created`
- `evidence.blocked`

原因：

- 这 8 条已经覆盖了项目创建、数据快照、分析执行、artifact 存证、assertion 落账和引文熔断。
- `review.*` 和 `export.completed` 可以放到 Sprint 4 再接，不会阻塞前 3 个 sprint 的主链路联调。
