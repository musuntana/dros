"""DR-OS API request/response models.

Aligned to docs/api-contracts.md and docs/fastapi-route-catalog.md.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .agents import AnalysisAgentResult, SearchResultItem, VerifierAgentResult
from .common import DRBaseModel, Page
from .domain import (
    AnalysisRunRead,
    AnalysisTemplateRead,
    ArtifactRead,
    AssertionRead,
    AuditEventRead,
    BlockAssertionLinkRead,
    DatasetRead,
    DatasetSnapshotRead,
    EvidenceLinkRead,
    EvidenceSourceRead,
    ExportJobRead,
    GateEvaluationRead,
    LineageEdgeRead,
    ManuscriptBlockRead,
    ManuscriptRead,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
    ReviewRead,
    WorkflowInstanceRead,
    WorkflowTaskRead,
)
from .enums import (
    ArtifactType,
    AssertionType,
    BlockType,
    EvidenceRelationType,
    EvidenceSourceType,
    ExportFormat,
    LicenseClass,
    LineageEdgeType,
    LineageKind,
    ManuscriptType,
    ReviewType,
    SectionKey,
    WorkflowBackend,
)


# ===========================================================================
# Session / Upload
# ===========================================================================

class SessionRead(DRBaseModel):
    actor_id: str
    principal_id: str
    tenant_id: str
    scopes_json: dict[str, Any] = Field(default_factory=dict)


class SignedUploadRequest(DRBaseModel):
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=1)


class SignedUploadResponse(DRBaseModel):
    upload_url: str
    object_key: str
    expires_in_seconds: int


class UploadCompleteRequest(DRBaseModel):
    object_key: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)


class UploadCompleteResponse(DRBaseModel):
    file_ref: str


class SignedArtifactUrlResponse(DRBaseModel):
    download_url: str
    expires_in_seconds: int


# ===========================================================================
# Projects
# ===========================================================================

class CreateProjectRequest(ProjectCreate):
    pass


class CreateProjectResponse(DRBaseModel):
    project: ProjectRead


class ProjectDetailResponse(DRBaseModel):
    project: ProjectRead
    active_workflows: list[WorkflowInstanceRead] = Field(default_factory=list)
    latest_snapshot: DatasetSnapshotRead | None = None
    active_manuscript: ManuscriptRead | None = None
    review_summary: dict[str, int] = Field(default_factory=dict)


class ProjectListResponse(DRBaseModel):
    items: Page[ProjectRead]


class AddProjectMemberRequest(ProjectMemberCreate):
    pass


class AddProjectMemberResponse(DRBaseModel):
    membership: ProjectMemberRead


class UpdateProjectRequest(ProjectUpdate):
    pass


class ProjectMemberListResponse(DRBaseModel):
    items: list[ProjectMemberRead]


# ===========================================================================
# Datasets
# ===========================================================================

class ImportPublicDatasetRequest(DRBaseModel):
    accession: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)


class RegisterUploadDatasetRequest(DRBaseModel):
    file_ref: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=255)


class CreateDatasetResponse(DRBaseModel):
    dataset: DatasetRead
    snapshot: DatasetSnapshotRead | None = None
    workflow_instance_id: UUID | None = None


class DatasetListResponse(DRBaseModel):
    items: Page[DatasetRead]


class DatasetDetailResponse(DRBaseModel):
    dataset: DatasetRead
    current_snapshot: DatasetSnapshotRead | None = None


class CreateDatasetSnapshotRequest(DRBaseModel):
    object_uri: str = Field(min_length=1)
    input_hash_sha256: str = Field(min_length=64, max_length=64)
    row_count: int | None = Field(default=None, ge=0)
    column_schema_json: dict[str, Any] = Field(default_factory=dict)


class CreateDatasetSnapshotResponse(DRBaseModel):
    snapshot: DatasetSnapshotRead


class DatasetSnapshotListResponse(DRBaseModel):
    items: list[DatasetSnapshotRead]


class DatasetPolicyCheckResponse(DRBaseModel):
    snapshot_id: UUID
    phi_scan_status: str
    deid_status: str
    blocking_reasons: list[str] = Field(default_factory=list)
    allowed: bool


# ===========================================================================
# Templates / Workflows / Analysis
# ===========================================================================

class TemplateListResponse(DRBaseModel):
    items: list[AnalysisTemplateRead]


class TemplateDetailResponse(DRBaseModel):
    template: AnalysisTemplateRead


class CreateAnalysisPlanRequest(DRBaseModel):
    study_goal: str = Field(min_length=10)
    dataset_ids: list[UUID] = Field(min_length=1)
    candidate_templates: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class CreateAnalysisPlanResponse(DRBaseModel):
    workflow_instance_id: UUID
    plan: AnalysisAgentResult


class CreateWorkflowRequest(DRBaseModel):
    workflow_type: str = Field(min_length=1)
    runtime_backend: WorkflowBackend = WorkflowBackend.QUEUE_WORKERS
    started_by: UUID | None = None
    parent_workflow_id: UUID | None = None


class CreateWorkflowResponse(DRBaseModel):
    workflow: WorkflowInstanceRead


class WorkflowListResponse(DRBaseModel):
    items: Page[WorkflowInstanceRead]


class WorkflowDetailResponse(DRBaseModel):
    workflow: WorkflowInstanceRead
    tasks: list[WorkflowTaskRead] = Field(default_factory=list)
    gate_evaluations: list[GateEvaluationRead] = Field(default_factory=list)


class AdvanceWorkflowRequest(DRBaseModel):
    task_id: UUID | None = None
    action: str | None = None
    comments: str | None = None


class CancelWorkflowRequest(DRBaseModel):
    reason: str = Field(min_length=1)
    requested_by: UUID | None = None


class CreateAnalysisRunRequest(DRBaseModel):
    snapshot_id: UUID
    template_id: UUID
    params_json: dict[str, Any] = Field(default_factory=dict)
    random_seed: int = 0
    workflow_instance_id: UUID | None = None


class CreateAnalysisRunResponse(DRBaseModel):
    analysis_run: AnalysisRunRead


class AnalysisRunDetailResponse(DRBaseModel):
    analysis_run: AnalysisRunRead
    artifacts: list[ArtifactRead] = Field(default_factory=list)


class AnalysisRunListResponse(DRBaseModel):
    items: Page[AnalysisRunRead]


# ===========================================================================
# Artifacts / Assertions / Lineage
# ===========================================================================

class CreateArtifactRequest(DRBaseModel):
    run_id: UUID | None = None
    artifact_type: ArtifactType
    storage_uri: str = Field(min_length=1)
    mime_type: str | None = None
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int | None = Field(default=None, ge=0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CreateArtifactResponse(DRBaseModel):
    artifact: ArtifactRead


class ArtifactListResponse(DRBaseModel):
    items: Page[ArtifactRead]


class ArtifactDetailResponse(DRBaseModel):
    artifact: ArtifactRead


class CreateAssertionRequest(DRBaseModel):
    assertion_type: AssertionType
    text_norm: str = Field(min_length=1)
    numeric_payload_json: dict[str, Any] = Field(default_factory=dict)
    source_run_id: UUID | None = None
    source_artifact_id: UUID | None = None
    source_span_json: dict[str, Any] = Field(default_factory=dict)
    claim_hash: str = Field(min_length=64, max_length=64)
    supersedes_assertion_id: UUID | None = None


class CreateAssertionResponse(DRBaseModel):
    assertion: AssertionRead


class AssertionListResponse(DRBaseModel):
    items: Page[AssertionRead]


class AssertionDetailResponse(DRBaseModel):
    assertion: AssertionRead
    evidence_links: list[EvidenceLinkRead] = Field(default_factory=list)
    block_links: list[BlockAssertionLinkRead] = Field(default_factory=list)


class CreateLineageEdgeRequest(DRBaseModel):
    from_kind: LineageKind
    from_id: UUID
    edge_type: LineageEdgeType
    to_kind: LineageKind
    to_id: UUID


class CreateLineageEdgeResponse(DRBaseModel):
    edge: LineageEdgeRead


class LineageQueryResponse(DRBaseModel):
    project_id: UUID
    edges: list[LineageEdgeRead] = Field(default_factory=list)
    artifacts: list[ArtifactRead] = Field(default_factory=list)
    assertions: list[AssertionRead] = Field(default_factory=list)
    analysis_runs: list[AnalysisRunRead] = Field(default_factory=list)


# ===========================================================================
# Evidence
# ===========================================================================

class EvidenceSearchRequest(DRBaseModel):
    query: str | None = Field(default=None, min_length=3)
    pico_question: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_query(self) -> "EvidenceSearchRequest":
        if not self.query and not self.pico_question:
            raise ValueError("query or pico_question is required")
        return self


class EvidenceSearchResponse(DRBaseModel):
    workflow_instance_id: UUID
    results: list[SearchResultItem] = Field(default_factory=list)


class ResolveEvidenceRequest(DRBaseModel):
    identifiers: list[str] = Field(min_length=1)


class ResolveEvidenceResponse(DRBaseModel):
    resolved: list[EvidenceSourceRead] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class UpsertEvidenceSourceRequest(DRBaseModel):
    source_type: EvidenceSourceType
    external_id_norm: str = Field(min_length=1)
    title: str = Field(min_length=1)
    doi_norm: str | None = None
    journal: str | None = None
    pub_year: int | None = Field(default=None, ge=1900, le=2200)
    pmid: str | None = None
    pmcid: str | None = None
    license_class: LicenseClass = LicenseClass.UNKNOWN
    oa_subset_flag: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class UpsertEvidenceSourceResponse(DRBaseModel):
    evidence_source: EvidenceSourceRead


class EvidenceSourceListResponse(DRBaseModel):
    items: Page[EvidenceSourceRead]


class CreateEvidenceLinkRequest(DRBaseModel):
    assertion_id: UUID
    evidence_source_id: UUID
    relation_type: EvidenceRelationType
    source_chunk_id: UUID | None = None
    source_span_start: int | None = None
    source_span_end: int | None = None
    excerpt_hash: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_span(self) -> "CreateEvidenceLinkRequest":
        if (self.source_span_start is not None and self.source_span_end is not None
                and self.source_span_end < self.source_span_start):
            raise ValueError("source_span_end must be >= source_span_start")
        return self


class CreateEvidenceLinkResponse(DRBaseModel):
    evidence_link: EvidenceLinkRead


class VerifyEvidenceLinkResponse(DRBaseModel):
    evidence_link: EvidenceLinkRead


class EvidenceLinkListResponse(DRBaseModel):
    items: Page[EvidenceLinkRead]


# ===========================================================================
# Manuscripts
# ===========================================================================

class CreateManuscriptRequest(DRBaseModel):
    manuscript_type: ManuscriptType = ManuscriptType.MANUSCRIPT
    title: str = Field(min_length=1)
    target_journal: str | None = None
    style_profile_json: dict[str, Any] = Field(default_factory=dict)


class CreateManuscriptResponse(DRBaseModel):
    manuscript: ManuscriptRead


class ManuscriptListResponse(DRBaseModel):
    items: list[ManuscriptRead]


class ManuscriptDetailResponse(DRBaseModel):
    manuscript: ManuscriptRead


class CreateManuscriptBlockRequest(DRBaseModel):
    section_key: SectionKey
    block_order: int = Field(default=0, ge=0)
    block_type: BlockType = BlockType.TEXT
    content_md: str = Field(min_length=1)
    assertion_ids: list[UUID] = Field(default_factory=list)


class CreateManuscriptBlockResponse(DRBaseModel):
    block: ManuscriptBlockRead


class ManuscriptBlockListResponse(DRBaseModel):
    items: list[ManuscriptBlockRead]


class CreateManuscriptVersionRequest(DRBaseModel):
    base_version_no: int | None = Field(default=None, ge=1)
    reason: str | None = None


class CreateManuscriptVersionResponse(DRBaseModel):
    manuscript: ManuscriptRead


class RenderManuscriptResponse(DRBaseModel):
    blocks: list[ManuscriptBlockRead]
    warnings: list[str] = Field(default_factory=list)


# ===========================================================================
# Review / Verification / Export
# ===========================================================================

class CreateReviewRequest(DRBaseModel):
    review_type: ReviewType
    target_kind: LineageKind
    target_id: UUID
    reviewer_id: UUID | None = None
    checklist_json: list[dict[str, Any]] = Field(default_factory=list)
    comments: str | None = None


class CreateReviewResponse(DRBaseModel):
    review: ReviewRead


class ReviewListResponse(DRBaseModel):
    items: Page[ReviewRead]


class ReviewDecisionRequest(DRBaseModel):
    action: str = Field(min_length=1)
    comments: str | None = None


class ReviewDecisionResponse(DRBaseModel):
    review: ReviewRead


class RunVerificationRequest(DRBaseModel):
    manuscript_id: UUID | None = None
    target_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_targets(self) -> "RunVerificationRequest":
        if self.manuscript_id is None and not self.target_ids:
            raise ValueError("manuscript_id or target_ids is required")
        return self


class RunVerificationResponse(DRBaseModel):
    workflow_instance_id: UUID
    gate_evaluations: list[GateEvaluationRead] = Field(default_factory=list)
    verifier_result: VerifierAgentResult | None = None
    blocking_summary: list[str] = Field(default_factory=list)


class CreateExportJobRequest(DRBaseModel):
    manuscript_id: UUID
    format: ExportFormat


class CreateExportJobResponse(DRBaseModel):
    export_job: ExportJobRead


class ExportJobDetailResponse(DRBaseModel):
    export_job: ExportJobRead
    output_artifact: ArtifactRead | None = None


class ExportJobListResponse(DRBaseModel):
    items: Page[ExportJobRead]


# ===========================================================================
# Audit
# ===========================================================================

class AuditEventListResponse(DRBaseModel):
    events: Page[AuditEventRead]


class AuditEventDetailResponse(DRBaseModel):
    event: AuditEventRead


class AuditReplayResponse(DRBaseModel):
    valid: bool
    checked_count: int
    first_invalid_event_id: UUID | None = None
