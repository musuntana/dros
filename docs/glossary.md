# DR-OS Glossary

本文件定义 DR-OS 的唯一工程词表，并给出禁止回流的旧命名。

冲突时，以 `docs/product-architecture.md` 和 `docs/core-data-model.md` 为准；本文件负责把词表落成可执行约束。

## 1. Canonical Objects

| Canonical Term | Scope | Meaning |
| :--- | :--- | :--- |
| `tenant` | Access | 部署或机构租户边界 |
| `principal` | Access | 用户或服务账号 |
| `project` | Access | 科研项目聚合根 |
| `dataset` | Data | 数据集逻辑对象 |
| `dataset_snapshot` | Data | 不可变输入快照 |
| `workflow_instance` | Workflow | 主流程状态机实例 |
| `workflow_task` | Workflow | 工作流步骤状态 |
| `analysis_run` | Execution | 一次模板化分析执行 |
| `artifact` | Ledger | 图表、表格、JSON、导出稿等工件 |
| `lineage_edge` | Ledger | 可回放谱系边 |
| `evidence_source` | Evidence | 标准化证据源对象 |
| `evidence_chunk` | Evidence | 证据 span / chunk |
| `assertion` | Writing | 可验证的最小事实单元 |
| `evidence_link` | Writing | Assertion 到 EvidenceSource / EvidenceChunk 的绑定 |
| `manuscript` | Writing | 稿件聚合对象 |
| `manuscript_block` | Writing | 结构化稿件 block |
| `block_assertion_link` | Writing | Block 到 Assertion 的显式映射 |
| `review` | Governance | 人工审批单 |
| `export_job` | Governance | 导出任务 |
| `audit_event` | Governance | append-only 审计事件 |

## 2. Canonical Fields

| Canonical Field | Use | Do Not Use |
| :--- | :--- | :--- |
| `workflow_instance_id` | workflow 事件 / API / 运行态引用 | `workflow_run_id` |
| `template_id` | analysis template / agent plan 标识 | `bundle_id` |
| `template_version` | analysis template 版本字段 | `bundle_version` |
| `evidence_source_id` | 证据绑定与事件 | `evidence_id` |
| `section_key` | manuscript / writing agent section 字段 | `section` |
| `assertion_ids` | block 绑定 assertion | `anchors` |
| `text_norm` | assertion 文本规范化字段 | `statement_text` |
| `text_norm` | assertion 文本归一化内容 | `claim_text` |
| `source_refs` | generated assertion 的来源引用 | `support_refs` |
| `license_class` | 许可分类 | `license_type` |
| `oa_subset_flag` | PMC OA 标志位 | `oa_subset` |
| `phi_cleared` | PolicyContext 中的 PHI 放行标志 | 任意自定义布尔替代字段 |

## 3. Deprecated Vocabulary

以下旧名不得在代码、文档、契约中继续作为当前设计事实源使用：

- `workflow_run`, `workflow_runs`, `workflow_run_id`
- `review_event`, `review_events`
- `evidence_record`, `evidence_records`, `evidence_id`
- `assertion_support_link`, `assertion_support_links`
- `bundle_id`, `bundle_version`
- `statement_text`
- `claim_text`
- `support_refs`
- JSON 示例中的 `section`
- JSON / schema 字段中的 `anchors`
- `license_type`
- `oa_subset`

## 4. Guardrail Rule

- 新增 schema、API、事件、文档时，只能使用本文件中的 canonical term / field。
- 旧词如需在文档中出现，只允许出现在本文件，不允许散落到其他文件。
