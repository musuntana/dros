from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import DRBaseModel


class DomainEventEnvelope(DRBaseModel):
    event_id: UUID
    event_name: str = Field(min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    produced_by: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    request_id: str | None = None
    tenant_id: UUID
    project_id: UUID
    idempotency_key: str = Field(min_length=1)
    occurred_at: datetime


class ProjectCreatedPayload(DRBaseModel):
    project_id: UUID
    owner_id: UUID
    project_type: Literal["public_omics", "clinical_retrospective", "case_report", "grant"]
    status: Literal["draft", "running", "review_required", "approved", "archived"]


class ProjectCreatedEvent(DomainEventEnvelope):
    event_name: Literal["project.created"] = "project.created"
    payload: ProjectCreatedPayload


class DatasetSnapshotCreatedPayload(DRBaseModel):
    dataset_id: UUID
    snapshot_id: UUID
    snapshot_no: int = Field(ge=1)
    source_kind: Literal["upload", "geo", "tcga", "seer", "manual"]
    input_hash_sha256: str = Field(min_length=64, max_length=64)
    deid_status: Literal["not_required", "pending", "completed", "failed"]
    phi_scan_status: Literal["pending", "passed", "blocked", "needs_human"]


class DatasetSnapshotCreatedEvent(DomainEventEnvelope):
    event_name: Literal["dataset.snapshot.created"] = "dataset.snapshot.created"
    payload: DatasetSnapshotCreatedPayload


class DatasetSnapshotBlockedPayload(DRBaseModel):
    dataset_id: UUID
    snapshot_id: UUID
    blocked_checks: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1)


class DatasetSnapshotBlockedEvent(DomainEventEnvelope):
    event_name: Literal["dataset.snapshot.blocked"] = "dataset.snapshot.blocked"
    payload: DatasetSnapshotBlockedPayload


class WorkflowStartedPayload(DRBaseModel):
    workflow_instance_id: UUID
    workflow_type: str = Field(min_length=1)
    runtime_backend: Literal["queue_workers", "temporal"]
    state: Literal[
        "created",
        "retrieving",
        "retrieved",
        "structuring",
        "structured",
        "analyzing",
        "analyzed",
        "asserting",
        "asserted",
        "writing",
        "verifying",
        "approved",
        "blocked",
        "needs_human",
        "exported",
        "failed",
    ]
    input_refs: list[str] = Field(default_factory=list)


class WorkflowStartedEvent(DomainEventEnvelope):
    event_name: Literal["workflow.started"] = "workflow.started"
    payload: WorkflowStartedPayload


class AnalysisRunRequestedPayload(DRBaseModel):
    analysis_run_id: UUID
    workflow_instance_id: UUID | None = None
    snapshot_id: UUID
    template_id: UUID
    repro_fingerprint: str = Field(min_length=64, max_length=64)


class AnalysisRunRequestedEvent(DomainEventEnvelope):
    event_name: Literal["analysis.run.requested"] = "analysis.run.requested"
    payload: AnalysisRunRequestedPayload


class AnalysisRunSucceededPayload(DRBaseModel):
    analysis_run_id: UUID
    workflow_instance_id: UUID | None = None
    artifact_ids: list[UUID] = Field(default_factory=list)
    output_artifact_count: int = Field(ge=0)
    finished_at: datetime


class AnalysisRunSucceededEvent(DomainEventEnvelope):
    event_name: Literal["analysis.run.succeeded"] = "analysis.run.succeeded"
    payload: AnalysisRunSucceededPayload


class AnalysisRunFailedPayload(DRBaseModel):
    analysis_run_id: UUID
    workflow_instance_id: UUID | None = None
    exit_code: int | None = None
    error_class: str | None = None
    error_message_trunc: str | None = None


class AnalysisRunFailedEvent(DomainEventEnvelope):
    event_name: Literal["analysis.run.failed"] = "analysis.run.failed"
    payload: AnalysisRunFailedPayload


class ArtifactCreatedPayload(DRBaseModel):
    artifact_id: UUID
    run_id: UUID | None = None
    artifact_type: Literal[
        "dataset_snapshot",
        "result_json",
        "table",
        "figure",
        "log",
        "manifest",
        "docx",
        "pdf",
        "zip",
        "evidence_attachment",
    ]
    output_slot: str | None = None
    storage_uri: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)


class ArtifactCreatedEvent(DomainEventEnvelope):
    event_name: Literal["artifact.created"] = "artifact.created"
    payload: ArtifactCreatedPayload


class AssertionCreatedPayload(DRBaseModel):
    assertion_id: UUID
    assertion_type: Literal["background", "method", "result", "limitation"]
    state: Literal["draft", "verified", "blocked", "stale"]
    source_run_id: UUID | None = None
    source_artifact_id: UUID | None = None


class AssertionCreatedEvent(DomainEventEnvelope):
    event_name: Literal["assertion.created"] = "assertion.created"
    payload: AssertionCreatedPayload


class EvidenceLinkedPayload(DRBaseModel):
    assertion_id: UUID
    evidence_link_id: UUID
    evidence_source_id: UUID
    relation_type: Literal["supports", "contradicts", "method_ref", "background_ref"]
    verifier_status: Literal["pending", "passed", "warning", "blocked"]


class EvidenceLinkedEvent(DomainEventEnvelope):
    event_name: Literal["evidence.linked"] = "evidence.linked"
    payload: EvidenceLinkedPayload


class EvidenceBlockedPayload(DRBaseModel):
    assertion_id: UUID
    candidate_identifier: str | None = None
    reason: str = Field(min_length=1)
    needs_human_items: list[str] = Field(default_factory=list)


class EvidenceBlockedEvent(DomainEventEnvelope):
    event_name: Literal["evidence.blocked"] = "evidence.blocked"
    payload: EvidenceBlockedPayload


class ReviewRequestedPayload(DRBaseModel):
    review_id: UUID
    review_type: Literal["evidence", "analysis", "manuscript", "export"]
    target_kind: str = Field(min_length=1)
    target_id: UUID
    target_version_no: int | None = Field(default=None, ge=1)
    state: Literal["pending", "approved", "rejected", "changes_requested"]


class ReviewRequestedEvent(DomainEventEnvelope):
    event_name: Literal["review.requested"] = "review.requested"
    payload: ReviewRequestedPayload


class ReviewCompletedPayload(DRBaseModel):
    review_id: UUID
    review_type: Literal["evidence", "analysis", "manuscript", "export"]
    target_kind: str = Field(min_length=1)
    target_id: UUID
    target_version_no: int | None = Field(default=None, ge=1)
    state: Literal["pending", "approved", "rejected", "changes_requested"]
    reviewer_id: UUID | None = None
    decided_at: datetime | None = None


class ReviewCompletedEvent(DomainEventEnvelope):
    event_name: Literal["review.completed"] = "review.completed"
    payload: ReviewCompletedPayload


class ExportCompletedPayload(DRBaseModel):
    export_job_id: UUID
    manuscript_id: UUID
    output_artifact_id: UUID
    format: Literal["docx", "pdf", "zip"]
    completed_at: datetime


class ExportCompletedEvent(DomainEventEnvelope):
    event_name: Literal["export.completed"] = "export.completed"
    payload: ExportCompletedPayload


EVENT_SCHEMAS = {
    "project-created.schema.json": ProjectCreatedEvent,
    "dataset-snapshot-created.schema.json": DatasetSnapshotCreatedEvent,
    "dataset-snapshot-blocked.schema.json": DatasetSnapshotBlockedEvent,
    "workflow-started.schema.json": WorkflowStartedEvent,
    "analysis-run-requested.schema.json": AnalysisRunRequestedEvent,
    "analysis-run-succeeded.schema.json": AnalysisRunSucceededEvent,
    "analysis-run-failed.schema.json": AnalysisRunFailedEvent,
    "artifact-created.schema.json": ArtifactCreatedEvent,
    "assertion-created.schema.json": AssertionCreatedEvent,
    "evidence-linked.schema.json": EvidenceLinkedEvent,
    "evidence-blocked.schema.json": EvidenceBlockedEvent,
    "review-requested.schema.json": ReviewRequestedEvent,
    "review-completed.schema.json": ReviewCompletedEvent,
    "export-completed.schema.json": ExportCompletedEvent,
}


__all__ = [
    "DomainEventEnvelope",
    "ProjectCreatedEvent",
    "DatasetSnapshotCreatedEvent",
    "DatasetSnapshotBlockedEvent",
    "WorkflowStartedEvent",
    "AnalysisRunRequestedEvent",
    "AnalysisRunSucceededEvent",
    "AnalysisRunFailedEvent",
    "ArtifactCreatedEvent",
    "AssertionCreatedEvent",
    "EvidenceLinkedEvent",
    "EvidenceBlockedEvent",
    "ReviewRequestedEvent",
    "ReviewCompletedEvent",
    "ExportCompletedEvent",
    "EVENT_SCHEMAS",
]
