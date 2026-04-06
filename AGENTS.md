# AGENTS.md

## 1. 目标
本文件定义 DR-OS 中所有 Agent 和控制面组件的统一行为边界、输入输出约束、权限范围、核验规则和熔断机制。

目标不是提升生成自由度，而是确保系统内所有组件都服务于以下原则：
- 不伪造证据
- 不越权访问数据
- 不绕过模板执行分析
- 不输出无法追溯的文本
- 不绕过核验直接导出
- 不跳过 Assertion 直接引用原始结果

## 1.1 权威事实来源
Agent 和控制面约束只服从以下设计事实源：

1. `docs/product-architecture.md`
2. `docs/core-data-model.md`
3. `docs/glossary.md`
4. `docs/module-boundaries.md`
5. `docs/api-contracts.md`
6. `docs/fastapi-route-catalog.md`
7. `docs/event-contracts.md`
8. `contracts/events/*.schema.json`
9. `AGENTS.md`
10. `sql/ddl_research_ledger_v2.sql`

约束解释：
- 词表以 `tenant / project / dataset_snapshot / workflow_instance / analysis_run / artifact / assertion / evidence_source / evidence_link / review / export_job / audit_event` 为准
- Agent 协议默认 project-scoped，`tenant_id` 由 Gateway / Workflow Runtime 从鉴权上下文解析，不由 Agent 自行声明或切换
- 禁止词与字段回流由 `docs/glossary.md` 和 `backend/scripts/check_vocabulary.py` 统一约束

## 2. 全局原则
1. 所有 Agent 输出必须是结构化 JSON，不接受纯自由文本作为系统间协议。
2. 所有 Agent 都必须携带 `project_id`、`task_id`、`trace_id`。
3. 所有 Agent 只能访问完成任务所需的最小数据范围。
4. 所有 Agent 的输出都必须通过 JSON Schema 校验。
5. 所有 Agent 的关键动作都必须写入审计日志。
6. 任一 Agent 都无权绕过 Evidence Control Plane 或 Export Gate。
7. 任一 Agent 都不得生成、修改或执行未审核的统计代码。
8. 任一 Agent 都不得编造 PMID、PMCID、DOI、样本量、P 值、HR、OR、置信区间。
9. 涉及临床数据时，未完成去标识化前，不得将原始数据发送给 LLM。
10. Agent 发现证据不足、字段缺失或规则冲突时，必须显式返回 `blocked` 或 `needs_human`，不得自行脑补。
11. 段落不得直接引用 AnalysisRun，必须通过 `Assertion -> source_artifact_id / evidence_link` 回链事实来源。
12. 主干流程由确定性状态机驱动，Agent 只做局部智能节点。
13. discussion transcript 不是系统真相；立题讨论只能沉淀为结构化计划、artifact、review 和 audit_event。

## 3. 系统角色
DR-OS 采用 workflow-first, agent-last 架构。首版角色：

**非 Agent 组件（确定性服务）**：
- **Workflow Service**：状态机、路由、重试、人工审批。不参与内容生成，不承担语义推理。
- **Evidence Structuring Service**：规则抽取、字段映射、人工确认生成证据表。不纳入 Agent 名册。
- **Evidence Control Plane**：Citation Resolver、Claim-Evidence Binder、Data Consistency Checker、License Guard。规则驱动，不依赖 LLM。

**Agent 组件（局部智能节点）**：
- **Search Agent**：文献与公共数据检索
- **Analysis Agent**：模板选择和参数翻译
- **Writing Agent**：基于 verified Assertion 生成说明性文字
- **Verifier Agent**：执行 Evidence Control Plane 中 LLM 辅助部分（语义边界判定）

LangGraph 定位：
- 只在 Agent 组件内部使用
- 支持 HITL interrupts（审批暂停/恢复）
- 支持 time-travel/fork（回溯与分支实验）
- **不做**主流程编排器

### 3.1 Discussion Mode / Study Design Roundtable

`discussion mode` 是 `analysis_planning` workflow 的一种前置交互模式，不新增新的 top-level Agent 名册。

约束：

- `临床专家 / 统计顾问 / 文献秘书` 只是对现有 Agent 能力的角色化视角，不是新的持久化系统对象
- discussion mode 的 durable output 只能是结构化研究问题、analysis plan、planning artifact、review items、audit_event
- discussion transcript 不能直接作为导出稿件、assertion、模板执行输入或 EvidenceLink 的事实来源
- discussion mode 结束后仍必须回到白名单模板、Assertion 抽取、Evidence Control Plane 和 review gate

## 4. 统一状态机
所有任务必须运行在显式状态下。

允许状态：
- `created`
- `retrieving`
- `retrieved`
- `structuring`
- `structured`
- `analyzing`
- `analyzed`
- `asserting`（从结果抽取 Assertion）
- `asserted`
- `writing`
- `verifying`
- `approved`
- `blocked`
- `needs_human`
- `exported`
- `failed`

状态转换规则：
- 只有 Workflow Service 可以迁移任务状态
- Agent 只能返回建议状态，不直接改数据库最终状态
- 任一 `blocked` 状态必须附带 `blocking_reasons`
- 任一 `needs_human` 状态必须附带明确待确认项
- `analyzing` → `analyzed` → `asserting` → `asserted` 是强制顺序，不可跳过 Assertion 抽取

## 5. 统一对象定义

### 5.1 Artifact
系统内一切可追溯工件的统一抽象：
- 原始数据快照（Dataset Snapshot）
- Report Bundle 版本
- 分析运行记录
- 结果文件（JSON、CSV、图像、表格）
- 导出稿件

每个 Artifact 具备：
- 唯一 `artifact_id`
- 不可变 `content_hash`
- 对象存储 `storage_uri`
- 版本链（`superseded_by`）

### 5.2 Assertion
从 Artifact 或 EvidenceSource 派生的**可验证声明**：
- 统计声明：`HR=0.65, 95%CI 0.48-0.89, p=0.03`
- 描述声明：`图1: Kaplan-Meier 生存曲线`
- 引文声明：`Smith et al. (2024) 报告 5 年 OS 为 68%`

每个 Assertion 必须有：
- 明确的 `source_artifact_id` 或合法 `evidence_links`
- `source_span_json`：指向源内具体位置（表格行、JSON 字段、PMID 段落）
- `verification_status`

### 5.3 EvidenceLink
Assertion 与 `EvidenceSource / EvidenceChunk` 的显式绑定：
- `supports`：文献或证据支持 Assertion
- `contradicts`：文献或证据与 Assertion 冲突
- `method_ref`：Assertion 对应方法学引用
- `background_ref`：Assertion 对应背景性引用

说明：
- ManuscriptBlock 不直接拥有 EvidenceLink
- ManuscriptBlock 通过 `block_assertion_links` 绑定 Assertion
- Assertion 再通过 `evidence_links` 或 `source_artifact_id` 回链到事实来源

### 5.4 Artifact Lineage DAG
完整追溯链路：
```
Dataset Snapshot → Report Bundle Version → AnalysisRun →
Result Artifact → Assertion → EvidenceLink → ManuscriptBlock → Review
```

关键约束：
- 段落 → Assertion → Artifact/Evidence，三级追溯不跳级
- Artifact 被 supersede 后原版本仍可追溯
- 任何断链（孤立 block、悬空 Assertion）都会被 Claim-Evidence Binder 拦截

## 6. Agent 统一输入输出协议

### 6.1 通用输入字段
```json
{
  "project_id": "proj_123",
  "task_id": "task_123",
  "trace_id": "trace_123",
  "actor_id": "system_or_user_id",
  "task_type": "literature_search",
  "input_refs": ["dataset_1", "evidence_2"],
  "policy_context": {
    "compliance_level": "clinical",
    "allow_external_llm": false,
    "phi_cleared": true
  }
}
```

### 6.2 通用输出字段
```json
{
  "project_id": "proj_123",
  "task_id": "task_123",
  "trace_id": "trace_123",
  "agent_name": "search_agent",
  "status": "ok",
  "confidence": 0.92,
  "result": {},
  "artifacts_produced": [],
  "assertions_produced": [],
  "warnings": [],
  "blocking_reasons": [],
  "needs_human_items": []
}
```

约束：
- `status` 只允许：`ok`、`blocked`、`needs_human`、`failed`
- `confidence` 仅作辅助显示，不能替代规则校验
- `result` 内字段必须符合对应 Agent 的独立 Schema
- `artifacts_produced` 和 `assertions_produced` 用于 Lineage DAG 更新

## 7. Search Agent

### 7.1 职责
- 执行 PubMed/PMC/Entrez 结构化检索（优先）
- 执行 PMID/PMCID/DOI 去重和对齐
- 拉取标题、摘要、作者、期刊、年份等结构化元数据
- 返回候选证据集合供用户确认或下游抽取
- 语义检索（pgvector）仅做二阶段 rerank，不做首次召回

### 7.2 允许访问
- Entrez API（受 rate limiter 管控）
- PMC 元数据接口
- GEO/TCGA 公共目录元数据
- 项目内已有 EvidenceSource
- pgvector 检索索引（仅 rerank 用途）

### 7.3 NCBI 访问约束
- 无 API key：≤3 req/s
- 有 API key：≤10 req/s
- 大批量检索必须走 batch fetch（Entrez EPost + EFetch）
- 必须实现 response cache，相同查询 24h 内命中缓存
- PMC 全文：仅 Open Access Subset 可程序化批量获取
- 非 OA 文献：只拉取 metadata，不尝试全文下载
- 所有外部请求必须标记 `license_class` 和 `oa_subset_flag`

### 7.4 禁止行为
- 不得生成结论性医学建议
- 不得伪造引用标识
- 不得凭摘要补全全文中不存在的结果
- 不得向 Writing Agent 直接传递未经核验的"结论"文本
- 不得绕过 rate limiter 直接调用 NCBI

### 7.5 输出契约
```json
{
  "result": {
    "query": "EGFR lung adenocarcinoma prognosis",
    "search_strategy": "entrez_structured",
    "rerank_applied": false,
    "search_results": [
      {
        "pmid": "12345678",
        "pmcid": "PMC123456",
        "doi": "10.1000/example",
        "title": "...",
        "journal": "...",
        "year": 2024,
        "license_class": "pmc_oa_subset",
        "oa_subset_flag": true,
        "match_reason": "high_keyword_overlap",
        "dedupe_key": "PMID:12345678"
      }
    ]
  }
}
```

### 7.6 熔断条件
以下任一情况返回 `blocked`：
- 检索结果缺少可验证主键且无法补齐
- 来源站点返回异常导致字段不完整
- 用户要求引用不存在的文献标识
- rate limiter 触发后仍无法在合理时间内完成检索

## 8. Analysis Agent

### 8.1 职责
- 将研究问题映射到已批准 `analysis_template`（Report Bundle）
- 生成参数 JSON
- 检查输入数据是否满足模板前置条件
- 输出建议执行计划

### 8.2 允许访问
- Template Registry 中已审核 `analysis_template` 列表
- 数据集元数据（不含原始数据）
- 字段映射规则
- 历史成功参数模板

### 8.3 禁止行为
- 不得自由编写 R/Python 统计逻辑
- 不得执行 shell、notebook、SQL 写入
- 不得修改已审核模板源码
- 不得在结果未生成前虚构统计结论
- 不得访问未去标识化的临床数据

### 8.4 输出契约
```json
{
  "result": {
    "template_id": "survival.cox.v1",
    "template_version": "1.0.3",
    "parameter_json": {
      "time_column": "os_time",
      "event_column": "os_event",
      "group_column": "risk_group",
      "covariates": ["age", "stage"]
    },
    "preflight_checks": [
      "time_column_exists",
      "event_column_binary",
      "covariates_not_null"
    ]
  }
}
```

### 8.5 熔断条件
以下任一情况返回 `needs_human` 或 `blocked`：
- 无法在白名单 Bundle 中匹配研究任务
- 数据字段缺失或含义不清
- 同一任务存在多个统计路径且会显著影响结论

## 9. Writing Agent

### 9.1 职责
- 基于 verified Assertion 生成方法、结果、图表说明、证据摘要
- 为每个 block 绑定 `assertion_ids`
- 输出段落级结构化内容

### 9.2 允许访问
- 已通过 Evidence Control Plane 的 Assertion
- Assertion 关联的 Artifact 元数据（不直接访问原始结果文件）
- 已通过验证的 EvidenceSource
- 结构化写作模板
- 术语标准化词表

### 9.3 禁止行为
- 不得读取未核验的原始数值并直接写入正文
- 不得填补 Assertion 中不存在的 P 值、样本量、效应量
- 不得把相关性改写为因果性
- 不得使用"证明""显著优于"等超出证据边界的措辞，除非 Assertion 明确支持
- 不得绕过 Assertion 直接引用 AnalysisRun 结果

### 9.4 输出契约
```json
{
  "result": {
    "section_key": "results",
    "blocks": [
      {
        "block_id": "blk_001",
        "text": "Cox 回归显示该指标与总生存相关（HR=0.65, 95%CI 0.48-0.89, p=0.03）。",
        "assertion_ids": ["ast_001"]
      }
    ],
    "assertions": [
      {
        "assertion_id": "ast_001",
        "assertion_type": "result",
        "text_norm": "cox regression showed the marker was associated with overall survival",
        "source_refs": ["artifact:result_json:cox_summary"]
      }
    ]
  },
  "assertions_consumed": ["ast_001"]
}
```

### 9.5 文本生成强约束
- 文本中的所有数值必须能指向单一 Assertion
- Assertion 必须有明确的 `source_artifact_id` 或 `evidence_links`
- 任何"显著""相关""独立危险因素"等词汇必须有对应 Assertion 支持
- 文稿 block 必须通过 `block_assertion_links` 显式绑定 Assertion
- 引文句对应的 Assertion 必须至少有一条合法 `evidence_link`
- 结果句对应的 Assertion 必须能回链到结果 Artifact 或 Result JSON

### 9.6 熔断条件
以下任一情况返回 `blocked`：
- 缺少 `assertion_ids` 或 `block_assertion_links`
- Assertion 中不存在文本引用的数值或指标
- 用户要求生成未完成分析的结果段落
- Assertion 的 `verification_status` 不为 `verified`

## 10. Evidence Control Plane
独立于 Agent 体系的核心控制面，规则驱动，不依赖 LLM。

### 10.1 Citation Resolver
职责：
- PMID/PMCID/DOI 存在性验证
- 元数据拉取与字段完整性检查
- PMID ↔ PMCID 双向对齐、去重
- rate limiter 管控（无 key ≤3 req/s，有 key ≤10 req/s）
- response cache + batch fetch（EPost + EFetch）

输出：
```json
{
  "resolved": true,
  "pmid": "12345678",
  "pmcid": "PMC123456",
  "metadata_complete": true,
  "missing_fields": []
}
```

### 10.2 Claim-Evidence Binder
职责：
- 校验每个 ManuscriptBlock 是否通过 `block_assertion_links` 绑定到 Assertion
- 校验 Assertion 是否有合法 source（Artifact 或 EvidenceSource）
- 检测孤立 block（无绑定）
- 检测悬空 Assertion（无 block 引用且无审计原因）
- 检测断链（Assertion source 指向已被 supersede 且无替代的 Artifact）

输出：
```json
{
  "verdict": "blocked",
  "orphan_blocks": ["blk_003"],
  "dangling_assertions": ["ast_007"],
  "broken_chains": [
    {
      "assertion_id": "ast_005",
      "reason": "source_artifact superseded without replacement"
    }
  ]
}
```

### 10.3 Data Consistency Checker
职责：
- 正文数值 vs 结果 JSON 数值
- 图表标注 vs 统计 JSON
- 表格行列 vs 原始计算输出
- Assertion `text_norm` / 数值载荷 vs source Artifact 内容
- 跨 Assertion 一致性（同一指标在不同段落不矛盾）

输出：
```json
{
  "verdict": "blocked",
  "inconsistencies": [
    {
      "assertion_id": "ast_001",
      "field": "p_value",
      "text_value": "0.03",
      "source_value": "0.08",
      "source_artifact": "stats_result.json:line42"
    }
  ]
}
```

### 10.4 License Guard
职责：
- PMC Open Access Subset 许可校验
- 数据集使用条款合规检查
- 非 OA 全文标记为 metadata-only
- 输出 `license_status` 供导出服务判断

输出：
```json
{
  "evidence_source_id": "evi_123",
  "license_class": "pmc_oa_subset",
  "oa_subset_flag": true,
  "full_text_reusable": true,
  "restrictions": []
}
```

### 10.5 Verifier Agent（LLM 辅助层）
Evidence Control Plane 中唯一使用 LLM 的组件，仅处理硬规则无法覆盖的语义判定：
- 段落语义是否超出证据支持范围
- 结论措辞是否过度推断（相关性→因果性）
- 摘要是否改变了原文含义

约束：
- 低温度，结构化输出
- 不可独立阻断，必须输出结构化 verdict 供 Policy Service 决策
- 不可修改原始分析结果或文稿
- 不可自动修正，只给出阻断原因和建议动作

输出：
```json
{
  "result": {
    "verdict": "warning",
    "semantic_checks": [
      {
        "name": "ScopeControl",
        "status": "warning",
        "block_id": "blk_002",
        "message": "正文使用'证明'一词，但 Assertion 来源为观察性研究",
        "suggested_action": "replace_with_suggest_or_indicate"
      }
    ]
  }
}
```

## 11. Workflow Service 规则
Workflow Service 是确定性状态机，不使用 LLM。

路由规则：
- Search Agent 输出先入库再进入 Evidence Structuring Service
- Citation Resolver 在证据入库时同步校验
- Analysis Agent 输出必须经 Template Registry 白名单检查后才能进入 Runner
- Runner 输出 Artifact 后必须进入 Assertion 抽取阶段
- Writing Agent 只能消费 verified Assertion
- 导出前必须经过 Evidence Control Plane 全链路校验
- `blocked` 对象不得参与最终导出
- 每次人工审批都必须形成 `audit_event`

编排分层：
| 组件 | 阶段 | 职责 |
| :--- | :--- | :--- |
| Celery + Redis | MVP | 异步耗时任务（分析执行、批量检索、导出） |
| Temporal | P1/B 端 | 跨服务长流程（多步审批、跨系统同步） |
| LangGraph | 全阶段 | 单任务内 Agent 推理 + HITL interrupts |

## 12. 模板与执行边界

### 12.1 Report Bundle 规范
每个发布的 `analysis_template`（Report Bundle）必须包含：
- `template_id` + `version`
- `container_image_digest`：Runner 镜像锁定版本
- `script_hash`：R/Python 脚本内容哈希
- `schema.json`：输入参数 Schema
- `golden_dataset`：回归测试标准数据
- `expected_outputs`：预期输出校验基线
- `doc_template`：Quarto/R Markdown 参数化文档模板
- `approved_by` + `approved_at`

### 12.2 执行约束
1. Runner 只能执行 Template Registry 中已注册的模板。
2. 执行环境为 K8s Job，rootless Docker，默认断网。
3. 任意运行都必须记录：
   - `template_id` + `template_version`
   - `runner_image_digest`
   - `input_hash` + `output_hash`
   - `seed`
   - `started_at` + `finished_at`
4. Runner 只写 Artifact 到对象存储，不直接写业务数据库。
5. Artifact Emitter 负责元数据回写。

### 12.3 报告生成解耦
- **分析模板**：Quarto / R Markdown 参数化执行 → 结果 + 图表
- **交付模板**：Pandoc `--reference-doc` → DOCX 样式输出
- 两者独立版本管理

## 13. LLM 使用策略
- **Search Agent**：可用小模型或规则为主，LangGraph 可做查询改写
- **Analysis Agent**：低温度，重点做结构化参数映射
- **Writing Agent**：低温度，仅做受限自然语言生成，消费 Assertion
- **Verifier Agent**：规则优先（Evidence Control Plane），LLM 仅用于语义边界判定

统一要求：
- 默认低温度
- 禁止链路中间产出未结构化自由结论
- 禁止将系统 prompt、密钥、内部策略回显给用户
- LangGraph 仅做 Agent 内部节点，不做跨服务编排

## 14. 临床数据特别约束
- 未去标识化数据不得进入外部模型
- 患者姓名、身份证号、住院号、手机号、地址等字段必须先脱敏
- 任何导出表格默认不包含直接识别符
- 项目合规等级为 `clinical` 时，所有 Agent 输出都要额外通过 `PHICompliance` 检查
- 临床数据上传后第一步是 PHI 扫描 + 字段映射确认 + 去标识化，不是分析

## 15. NCBI 与外部数据源约束
- Entrez 结构化检索优先，语义检索仅做 rerank
- 无 API key：≤3 req/s；有 API key：≤10 req/s
- 大批量走 EPost + EFetch batch 模式
- 必须实现 response cache（相同查询 24h 内命中缓存）
- PMC 全文仅 Open Access Subset 可程序化批量获取
- 非 OA 文献只拉 metadata，不尝试全文下载
- 所有外部检索结果必须标记 `license_class` 和 `oa_subset_flag`
- GEO/TCGA 公共数据接入需遵循各自使用条款

## 16. 错误处理与降级策略
- 外部文献接口失败：返回 `needs_human`，允许用户手动补录 PMID
- rate limiter 触发：排队等待，不降级为无限制调用
- 模板预检查失败：阻断执行并返回缺失字段列表
- Evidence Control Plane 校验失败：阻断导出，不自动洗稿
- 对象存储写入失败：任务进入 `failed`，不得假设成功
- 向量检索不可用：降级为 FTS/BM25 关键词检索，不影响核心可追溯链路
- Assertion 抽取失败：任务进入 `needs_human`，不跳过 Assertion 阶段

## 17. 审计要求
以下动作必须记录到 `audit_events`：
- 用户上传数据
- 用户确认字段映射
- PHI 扫描结果
- Evidence Structuring Service 生成或修改证据表
- Assertion 创建、supersede、阻断
- Report Bundle 选择与参数变更
- K8s Job 启动与完成
- Artifact 写入对象存储
- Writing Agent 生成文稿 block
- EvidenceLink 创建和核验结论
- Evidence Control Plane 各组件校验结果
- Verifier Agent 语义判定结果
- 人工审批（Approve / Reject / Edit）
- 导出与分享

## 18. 禁止事项清单
所有 Agent 和系统组件一律禁止：
- 编造证据
- 编造统计结果
- 绕过 Template Registry
- 绕过 Evidence Control Plane
- 跳过 Assertion 直接在段落引用原始结果
- 修改审计日志
- 使用未授权外部数据源
- 将原始临床数据泄露给无权组件
- 用自由文本替代结构化系统接口
- 绕过 rate limiter 调用 NCBI
- 在断网沙箱外执行分析脚本

## 19. 发布前检查清单
上线前必须确认：
- [ ] 所有 Agent JSON Schema 已固化并有测试
- [ ] Evidence Control Plane 4 个子组件均可独立运行和测试
- [ ] Gate 失败能真实阻断导出
- [ ] 任意 ManuscriptBlock 都能通过 Assertion → Artifact/Evidence 追溯
- [ ] Lineage DAG 无孤立节点和断链
- [ ] NCBI rate limiter + cache 正常工作
- [ ] License Guard 正确区分 OA / 非 OA
- [ ] 临床模式下 PHI 检查默认开启
- [ ] Report Bundle 版本可追溯
- [ ] K8s Job rootless + 断网沙箱生效
- [ ] RLS + FORCE ROW LEVEL SECURITY 对 table owner 生效
- [ ] 审计事件可导出且写入 WORM
- [ ] OTel traces 覆盖关键链路

## 20. 结论
DR-OS 中的价值不在于"Agent 更聪明"，而在于"Artifact Lineage 更完整"。

Agent 是局部智能节点，Evidence Control Plane 是规则门禁，Research Ledger 是全局真相源。只有当所有组件都被限制在明确的权限、输入输出协议和 Assertion 追溯链路内，系统才能在医学科研场景里建立可信度。
