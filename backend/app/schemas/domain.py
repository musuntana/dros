"""DR-OS domain models aligned to core-data-model.md and ddl_research_ledger_v2.sql.

Organized by the four layers in core-data-model.md:
1. Tenant & Access
2. Data & Execution
3. Evidence & Writing
4. Governance
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .common import DRBaseModel, TimestampedModel
from .enums import (
    ActorType,
    AgentName,
    AnalysisRunState,
    ArtifactType,
    AssertionState,
    AssertionType,
    BlockState,
    BlockType,
    ComplianceLevel,
    DatasetSourceKind,
    DeidStatus,
    EvidenceRelationType,
    EvidenceSourceType,
    ExportFormat,
    ExportState,
    GateName,
    GateStatus,
    LicenseClass,
    LineageEdgeType,
    LineageKind,
    ManuscriptState,
    ManuscriptType,
    PhiScanStatus,
    PiiLevel,
    ProjectRole,
    ProjectState,
    ProjectType,
    ReviewState,
    ReviewType,
    SectionKey,
    TaskState,
    TemplateReviewStatus,
    VerifierStatus,
    WorkflowBackend,
    WorkflowState,
)


# ===========================================================================
# 1. Tenant & Access
# ===========================================================================

class TenantRead(TimestampedModel):
    id: UUID
    name: str
    tier: str
    deployment_mode: str
    status: str


class PrincipalRead(TimestampedModel):
    id: UUID
    tenant_id: UUID
    subject_type: str
    external_sub: str
    email: str | None = None
    display_name: str
    status: str


class ProjectCreate(DRBaseModel):
    name: str = Field(min_length=1, max_length=200)
    project_type: ProjectType
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    owner_id: UUID


class ProjectUpdate(DRBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: ProjectState | None = None
    compliance_level: ComplianceLevel | None = None
    active_manuscript_id: UUID | None = None


class ProjectRead(TimestampedModel):
    id: UUID
    tenant_id: UUID
    name: str
    project_type: ProjectType
    status: ProjectState
    compliance_level: ComplianceLevel
    owner_id: UUID
    active_manuscript_id: UUID | None = None


class ProjectMemberCreate(DRBaseModel):
    principal_id: UUID
    role: ProjectRole


class ProjectMemberRead(DRBaseModel):
    project_id: UUID
    principal_id: UUID
    role: ProjectRole
    scopes_json: dict[str, Any] = Field(default_factory=dict)
    joined_at: datetime


# ===========================================================================
# 2. Data & Execution
# ===========================================================================

class DatasetCreate(DRBaseModel):
    source_kind: DatasetSourceKind
    display_name: str = Field(min_length=1, max_length=255)
    source_ref: str | None = None
    pii_level: PiiLevel = PiiLevel.NONE
    license_class: LicenseClass = LicenseClass.UNKNOWN


class DatasetRead(TimestampedModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    source_kind: DatasetSourceKind
    display_name: str
    source_ref: str | None = None
    pii_level: PiiLevel
    license_class: LicenseClass
    current_snapshot_id: UUID | None = None


class DatasetSnapshotCreate(DRBaseModel):
    object_uri: str = Field(min_length=1)
    input_hash_sha256: str = Field(min_length=64, max_length=64)
    row_count: int | None = Field(default=None, ge=0)
    column_schema_json: dict[str, Any] = Field(default_factory=dict)


class DatasetSnapshotRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    dataset_id: UUID
    snapshot_no: int
    object_uri: str
    input_hash_sha256: str
    row_count: int | None = None
    column_schema_json: dict[str, Any]
    deid_status: DeidStatus
    phi_scan_status: PhiScanStatus
    created_at: datetime


class AnalysisTemplateRead(DRBaseModel):
    id: UUID
    tenant_id: UUID | None = None
    code: str
    version: str
    name: str
    image_digest: str
    script_hash: str
    param_schema_json: dict[str, Any]
    output_schema_json: dict[str, Any]
    golden_dataset_uri: str | None = None
    expected_outputs_json: dict[str, Any] = Field(default_factory=dict)
    doc_template_uri: str | None = None
    review_status: TemplateReviewStatus
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime


class WorkflowInstanceCreate(DRBaseModel):
    workflow_type: str = Field(min_length=1)
    runtime_backend: WorkflowBackend = WorkflowBackend.QUEUE_WORKERS
    started_by: UUID | None = None
    parent_workflow_id: UUID | None = None


class WorkflowInstanceRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    workflow_type: str
    state: WorkflowState
    current_step: str | None = None
    parent_workflow_id: UUID | None = None
    started_by: UUID | None = None
    runtime_backend: WorkflowBackend
    started_at: datetime
    ended_at: datetime | None = None


class WorkflowTaskRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    workflow_instance_id: UUID
    task_key: str
    task_type: str
    state: TaskState
    assignee_id: UUID | None = None
    input_payload_json: dict[str, Any]
    output_payload_json: dict[str, Any]
    retry_count: int
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AnalysisRunCreate(DRBaseModel):
    project_id: UUID
    snapshot_id: UUID
    template_id: UUID
    params_json: dict[str, Any] = Field(default_factory=dict)
    random_seed: int = 0
    workflow_instance_id: UUID | None = None
    rerun_of_run_id: UUID | None = None


class AnalysisRunRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    workflow_instance_id: UUID | None = None
    snapshot_id: UUID
    template_id: UUID
    state: AnalysisRunState
    params_json: dict[str, Any]
    param_hash: str
    random_seed: int
    container_image_digest: str
    repro_fingerprint: str
    runtime_manifest_json: dict[str, Any]
    input_artifact_manifest_json: list[Any]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    rerun_of_run_id: UUID | None = None
    job_ref: str | None = None
    error_class: str | None = None
    error_message_trunc: str | None = None
    created_at: datetime


class ArtifactCreate(DRBaseModel):
    project_id: UUID
    run_id: UUID | None = None
    artifact_type: ArtifactType
    output_slot: str | None = None
    storage_uri: str = Field(min_length=1)
    mime_type: str | None = None
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int | None = Field(default=None, ge=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ArtifactRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    run_id: UUID | None = None
    artifact_type: ArtifactType
    output_slot: str | None = None
    storage_uri: str
    mime_type: str | None = None
    sha256: str
    size_bytes: int | None = None
    metadata_json: dict[str, Any]
    superseded_by: UUID | None = None
    created_at: datetime


class LineageEdgeCreate(DRBaseModel):
    project_id: UUID
    from_kind: LineageKind
    from_id: UUID
    edge_type: LineageEdgeType
    to_kind: LineageKind
    to_id: UUID


class LineageEdgeRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    from_kind: LineageKind
    from_id: UUID
    edge_type: LineageEdgeType
    to_kind: LineageKind
    to_id: UUID
    created_at: datetime


# ===========================================================================
# 3. Evidence & Writing
# ===========================================================================

class EvidenceSourceRead(DRBaseModel):
    """Global evidence source — not project-scoped (deduped by external_id_norm)."""
    id: UUID
    source_type: EvidenceSourceType
    external_id_norm: str
    doi_norm: str | None = None
    title: str
    journal: str | None = None
    pub_year: int | None = None
    pmid: str | None = None
    pmcid: str | None = None
    license_class: LicenseClass
    oa_subset_flag: bool
    metadata_json: dict[str, Any]
    cached_at: datetime


class EvidenceChunkRead(DRBaseModel):
    id: UUID
    evidence_source_id: UUID
    chunk_no: int
    section_label: str | None = None
    text: str
    char_start: int
    char_end: int
    token_count: int
    created_at: datetime


class AssertionCreate(DRBaseModel):
    assertion_type: AssertionType
    text_norm: str = Field(min_length=1)
    numeric_payload_json: dict[str, Any] = Field(default_factory=dict)
    source_run_id: UUID | None = None
    source_artifact_id: UUID | None = None
    source_span_json: dict[str, Any] = Field(default_factory=dict)
    claim_hash: str = Field(min_length=64, max_length=64)
    supersedes_assertion_id: UUID | None = None


class AssertionRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    assertion_type: AssertionType
    text_norm: str
    numeric_payload_json: dict[str, Any]
    source_run_id: UUID | None = None
    source_artifact_id: UUID | None = None
    source_span_json: dict[str, Any]
    claim_hash: str
    state: AssertionState
    supersedes_assertion_id: UUID | None = None
    created_at: datetime


class EvidenceLinkCreate(DRBaseModel):
    assertion_id: UUID
    evidence_source_id: UUID
    relation_type: EvidenceRelationType
    source_chunk_id: UUID | None = None
    source_span_start: int | None = None
    source_span_end: int | None = None
    excerpt_hash: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_span(self) -> "EvidenceLinkCreate":
        if (self.source_span_start is not None and self.source_span_end is not None
                and self.source_span_end < self.source_span_start):
            raise ValueError("source_span_end must be >= source_span_start")
        return self


class EvidenceLinkRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    assertion_id: UUID
    evidence_source_id: UUID
    relation_type: EvidenceRelationType
    source_chunk_id: UUID | None = None
    source_span_start: int | None = None
    source_span_end: int | None = None
    excerpt_hash: str | None = None
    verifier_status: VerifierStatus
    confidence: float | None = None
    created_at: datetime


class ManuscriptCreate(DRBaseModel):
    manuscript_type: ManuscriptType = ManuscriptType.MANUSCRIPT
    title: str = Field(min_length=1)
    target_journal: str | None = None
    style_profile_json: dict[str, Any] = Field(default_factory=dict)


class ManuscriptRead(TimestampedModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    manuscript_type: ManuscriptType
    title: str
    state: ManuscriptState
    current_version_no: int
    style_profile_json: dict[str, Any]
    target_journal: str | None = None
    created_by: UUID | None = None


class ManuscriptBlockCreate(DRBaseModel):
    section_key: SectionKey
    block_order: int = Field(default=0, ge=0)
    block_type: BlockType = BlockType.TEXT
    content_md: str = Field(min_length=1)
    assertion_ids: list[UUID] = Field(default_factory=list)


class ManuscriptBlockRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    manuscript_id: UUID
    version_no: int
    section_key: SectionKey
    block_order: int
    block_type: BlockType
    content_md: str
    status: BlockState
    supersedes_block_id: UUID | None = None
    created_at: datetime
    assertion_ids: list[UUID] = Field(default_factory=list)


class BlockAssertionLinkCreate(DRBaseModel):
    block_id: UUID
    assertion_id: UUID
    render_role: str = Field(min_length=1)
    display_order: int = Field(default=0, ge=0)


class BlockAssertionLinkRead(DRBaseModel):
    block_id: UUID
    assertion_id: UUID
    render_role: str
    display_order: int
    created_at: datetime


# ===========================================================================
# 4. Governance
# ===========================================================================

class ReviewCreate(DRBaseModel):
    review_type: ReviewType
    target_kind: LineageKind
    target_id: UUID
    target_version_no: int | None = Field(default=None, ge=1)
    reviewer_id: UUID | None = None
    checklist_json: list[dict[str, Any]] = Field(default_factory=list)
    comments: str | None = None


class ReviewRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    review_type: ReviewType
    target_kind: LineageKind
    target_id: UUID
    target_version_no: int | None = Field(default=None, ge=1)
    state: ReviewState
    reviewer_id: UUID | None = None
    checklist_json: list[dict[str, Any]]
    comments: str | None = None
    decided_at: datetime | None = None
    created_at: datetime


class ExportJobCreate(DRBaseModel):
    manuscript_id: UUID
    format: ExportFormat


class ExportJobRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    manuscript_id: UUID
    format: ExportFormat
    state: ExportState
    output_artifact_id: UUID | None = None
    requested_by: UUID | None = None
    requested_at: datetime
    completed_at: datetime | None = None


class AuditEventRead(DRBaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID | None = None
    actor_id: UUID | None = None
    actor_type: ActorType
    event_type: str
    target_kind: LineageKind
    target_id: UUID | None = None
    request_id: str | None = None
    trace_id: str | None = None
    payload_json: dict[str, Any]
    prev_hash: str | None = None
    event_hash: str
    created_at: datetime


# ===========================================================================
# Application-level: Gate evaluation (not in DDL, used by verify endpoint)
# ===========================================================================

class GateEvaluationRead(DRBaseModel):
    verification_id: UUID | None = None
    gate_name: GateName
    target_kind: LineageKind
    target_id: UUID
    status: GateStatus
    details_json: dict[str, Any] = Field(default_factory=dict)
    evaluated_by: AgentName | None = None
    evaluated_at: datetime
