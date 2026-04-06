# DR-OS Event Sequences

## 1. 目标

本文件定义 DR-OS 的关键时序流。它不是接口文档，而是系统行为文档，用于统一前端、控制面、工作流、执行面和账本层的协作方式。

事件名与幂等键的权威定义见 `docs/event-contracts.md` 和 `contracts/events/*.schema.json`。

## 2. 事件设计原则

1. 业务状态变更优先落账，再广播事件。
2. 长任务状态由 `workflow_instances` 驱动，而不是由前端轮询猜测。
3. 任何可导出的内容都必须经过 verify / review / export 三步。
4. 任何跨对象引用都必须最终落到 assertion 或 lineage 上。
5. 事件必须带 `tenant_id`、`project_id`、`trace_id`、`idempotency_key`。
6. `Research Canvas` 的 timeline 是领域事件、workflow detail 和 audit_event 的联合投影，不是 raw agent transcript。
7. rollback / resume 通过 child workflow、新版本和 supersede 链表达，不设计 mutable undo 事件。

## 3. 前置流程：立题讨论 -> Analysis Plan

```mermaid
sequenceDiagram
  autonumber
  actor U as 用户
  participant C as Research Canvas
  participant G as BFF/Gateway
  participant W as Workflow Service
  participant L as LangGraph Nodes
  participant E as Evidence Service
  participant A as Artifact Service
  participant R as Review&Policy

  U->>C: 进入 discussion mode，填写研究方向
  C->>G: POST /analysis/plans
  G->>W: create analysis_planning workflow
  W->>L: 启动受控多角色 roundtable
  L->>E: 补充检索线索与证据缺口
  E-->>L: candidate evidence / metadata
  L-->>W: 结构化研究问题、终点、协变量、模板建议
  W->>A: register planning artifact
  W->>R: review.requested(target=workflow/artifact)
  R-->>C: 待确认的 analysis plan
  U->>C: 确认或修改研究问题
  C->>G: POST /workflows/{workflow_instance_id}/advance
  G->>W: 标记 plan ready
```

补充：

- discussion transcript 不是正式真相源；durable output 只能是 planning artifact、workflow task payload、review 和 audit_event
- 该流程的实时 UI 主要依赖 `workflow.started`、`review.requested` 与通用审计事件投影

## 4. 主流程一：公共数据库课题 -> 分析 -> 证据绑定 -> 初稿

```mermaid
sequenceDiagram
  autonumber
  actor U as 用户
  participant C as Research Canvas
  participant G as BFF/Gateway
  participant P as Project Service
  participant D as Dataset Service
  participant W as Workflow Service
  participant Q as Queue/Temporal
  participant B as Job Broker
  participant R as K8s Runner
  participant A as Artifact Service
  participant E as Evidence Service
  participant M as Manuscript Service
  participant V as Review Service

  U->>C: 新建项目，选择 TCGA/GEO 课题模板
  C->>G: POST /projects + /datasets/import-public
  G->>P: createProject()
  P-->>G: project_id
  G->>D: importPublicDataset(accession)
  D->>D: 生成 dataset + snapshot + input_hash
  D-->>W: dataset.snapshot.created
  W->>Q: startWorkflow(project_id, snapshot_id, template_id)
  Q->>B: analysis.run.requested
  B->>R: create job(bundle, params, snapshot)
  R->>R: 执行 R / Python / Quarto 模板
  R-->>A: register plot / table / json / log / manifests
  A-->>W: artifact.created
  W->>M: create assertions from result JSON
  M-->>E: assertion.created
  E->>E: resolve / bind evidence
  alt 核验通过
    E-->>M: evidence.linked
    M-->>V: review.requested(target=manuscript)
    V-->>C: 初稿待审核
  else 引文或数据不一致
    E-->>V: evidence.blocked
    V-->>C: 阻断并提示人工修复
  end
```

补充：

- 浏览器侧 `Research Canvas` 当前通过 frontend 同源 `/api/projects/{project_id}/events` proxy 订阅 Gateway SSE，而不是在页面直接拼 backend URL
- workspace 左栏当前会把 recent audit seed 与 live SSE 事件合并展示；用户选中某条事件后，Inspector 会同步显示 `trace / request / payload` 和跨对象跳转
- 推荐阶段标签：
  - `数据导入中`：`workflow.state in retrieving|structuring`
  - `模板运行中`：`analysis.run.requested` 到 `analysis.run.succeeded|failed`
  - `证据核验中`：`assertion.created` 到 `evidence.linked|evidence.blocked`
  - `稿件待审中`：`review.requested`

核心事件：

- `project.created`
- `dataset.snapshot.created`
- `workflow.started`
- `analysis.run.requested`
- `analysis.run.succeeded`
- `artifact.created`
- `assertion.created`
- `evidence.linked`
- `evidence.blocked`
- `review.requested`

## 5. 主流程二：临床 Excel 上传 -> 存证 -> 脱敏门禁 -> 统计分析

```mermaid
sequenceDiagram
  autonumber
  actor U as 用户
  participant C as Research Canvas
  participant G as BFF/Gateway
  participant S as Object Storage
  participant D as Dataset Service
  participant P as Review&Policy
  participant W as Workflow Service
  participant Q as Queue/Temporal
  participant B as Job Broker
  participant R as K8s Runner
  participant A as Artifact Service

  U->>C: 上传临床 Excel
  C->>G: POST /uploads/sign
  G-->>C: signed_url
  C->>S: PUT file
  C->>G: POST /uploads/complete
  G-->>C: file_ref
  C->>D: POST /datasets/register-upload
  D->>D: create dataset + snapshot
  D->>D: 计算 sha256 / schema scan / row_count
  D->>P: PII & de-identification check
  alt 策略通过
    P-->>W: allow workflow start
    W->>Q: start retrospective workflow
    Q->>B: analysis.run.requested
    B->>R: create job
    R-->>A: store tables / plots / result_json
    A-->>C: SSE progress + artifact preview
  else 触发策略阻断
    P-->>D: dataset.snapshot.blocked
    D-->>C: blocked(reason=PII/deid/license)
  end
```

补充：

- artifact payload 下载当前不在浏览器侧直接消费 gateway `download-url`；前端会调用同源 `/api/projects/{project_id}/artifacts/{artifact_id}/download` route，由服务端解析本地 `file://` 或执行外部重定向
- 推荐阶段标签：
  - `数据导入中`：上传完成到 policy check 返回
  - `模板运行中`：`analysis.run.requested` 之后
  - `证据核验中`：analysis 后的 assertion / evidence 阶段
  - `稿件待审中`：有 review request 但尚未决定

核心事件：

- `dataset.snapshot.created`
- `dataset.snapshot.blocked`
- `workflow.started`
- `analysis.run.requested`
- `analysis.run.succeeded`
- `analysis.run.failed`
- `artifact.created`

## 6. 主流程三：反幻觉引文熔断 -> 人工修复 -> 重新核验

```mermaid
sequenceDiagram
  autonumber
  actor U as 用户
  participant M as Manuscript Service
  participant E as Evidence Service
  participant V as Review&Policy
  participant C as Research Canvas

  M->>E: resolveCitation(assertion_text, candidate_pmid/doi)
  E->>E: normalize PMID / PMCID / DOI
  alt 找到文献且 span 可定位
    E-->>M: evidence.linked(verifier_status=passed)
    M-->>C: block status = verified
  else 未找到 / 不支持 / span 不匹配
    E-->>V: evidence.blocked
    V-->>C: 显示“禁止自动引文”，需人工补充
    U->>C: 手动补 PMID/DOI 或删除该句
    C->>E: re-verify
    alt 人工修复成功
      E-->>M: evidence.linked
      M-->>C: block status = verified
    else 仍失败
      E-->>C: 保持 blocked，不允许导出正式稿
    end
  end
```

核心事件：

- `assertion.created`
- `evidence.linked`
- `evidence.blocked`
- `review.requested`

## 7. 产品交互：版本级 Rollback / Resume

```mermaid
sequenceDiagram
  autonumber
  actor U as 用户
  participant C as Research Canvas
  participant G as BFF/Gateway
  participant W as Workflow Service
  participant M as Manuscript Service
  participant A as Artifact Service

  U->>C: 选择历史 workflow / manuscript version
  C->>G: POST /workflows or /manuscripts/{id}/versions
  G->>W: create child workflow(parent_workflow_id=...)
  G->>M: create new manuscript version(base_version_no=...)
  W-->>C: 新的 workflow_instance
  M-->>C: 新的 current manuscript version
  A-->>C: inspector 展示 parent / supersedes / version 链
```

补充：

- 该交互不引入 `undo` 事件；链路依赖 `parent_workflow_id`、artifact `supersedes`、`version_no` 和对应审计
- 历史对象保持只读，新版本才允许继续写作、核验和导出

## 8. 审核、核验与导出

```mermaid
sequenceDiagram
  autonumber
  actor U as Reviewer
  participant C as Review Queue
  participant G as BFF/Gateway
  participant R as Review&Policy
  participant W as Workflow Service
  participant M as Manuscript Service
  participant X as Export Service

  U->>C: 点击 Verify
  C->>G: POST /verify
  G->>R: run gate evaluations + verifier assist
  R->>W: create verification workflow
  W-->>C: workflow.started
  alt 存在阻断项
    R-->>C: blocking summary
    U->>C: request changes / reject
    C->>G: POST /reviews/{id}/decisions
    G->>R: record review decision
    R-->>M: review.completed
  else 全部通过
    U->>C: 发起导出
    C->>G: POST /exports
    G->>X: create export job
    X-->>C: export.completed
  end
```

核心事件：

- `workflow.started`
- `review.requested`
- `review.completed`
- `export.completed`

## 9. 推荐事件命名集合

当前主链路只使用以下领域事件：

- `project.created`
- `dataset.snapshot.created`
- `dataset.snapshot.blocked`
- `workflow.started`
- `analysis.run.requested`
- `analysis.run.succeeded`
- `analysis.run.failed`
- `artifact.created`
- `assertion.created`
- `evidence.linked`
- `evidence.blocked`
- `review.requested`
- `review.completed`
- `export.completed`

## 10. 结论

DR-OS 最关键的不是“能不能生成一段话”，而是：

- 这段话对应哪个 assertion
- 这个 assertion 对应哪些 artifact 和 evidence
- 这些对象经过了哪些 verify / review
- 当前导出版本是否能完整回放这条链路

时序设计的目标，就是让这些问题都能被系统默认回答。
