from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..object_store import build_export_object_key, storage_uri_for_key, write_object_bytes
from ..repositories.base import append_audit_event
from ..schemas.api import (
    CreateExportJobRequest,
    CreateExportJobResponse,
    ExportJobDetailResponse,
    ExportJobListResponse,
)
from ..schemas.domain import ArtifactRead, ExportJobRead, LineageEdgeRead, ManuscriptRead
from ..schemas.enums import (
    ArtifactType,
    AssertionState,
    ExportState,
    GateStatus,
    LineageEdgeType,
    LineageKind,
    ManuscriptState,
)
from .base import BaseService


@dataclass(slots=True)
class ExportService(BaseService):
    repository: object

    def create_export_job(self, project_id: UUID, payload: CreateExportJobRequest) -> CreateExportJobResponse:
        self._require_project(project_id, "exports:write")
        manuscript = self._require_manuscript(project_id, payload.manuscript_id, "exports:write")
        blocking_reasons = self._collect_blocking_reasons(project_id, manuscript)
        now = self.now()
        output_artifact = None
        state = ExportState.BLOCKED if blocking_reasons else ExportState.COMPLETED
        output_artifact_id = None
        completed_at = now if state == ExportState.COMPLETED else None

        if state == ExportState.COMPLETED:
            output_artifact = self._build_output_artifact(project_id, manuscript, payload.format.value, now)
            self.repository.store.artifacts[output_artifact.id] = output_artifact
            output_artifact_id = output_artifact.id
            edge = LineageEdgeRead(
                id=uuid4(),
                tenant_id=self.repository.tenant_id,
                project_id=project_id,
                from_kind=LineageKind.MANUSCRIPT,
                from_id=manuscript.id,
                edge_type=LineageEdgeType.EXPORTS,
                to_kind=LineageKind.ARTIFACT,
                to_id=output_artifact.id,
                created_at=now,
            )
            self.repository.store.lineage_edges[edge.id] = edge
            self.repository.store.manuscripts[manuscript.id] = manuscript.model_copy(
                update={"state": ManuscriptState.EXPORTED, "updated_at": now}
            )

        export_job = ExportJobRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            manuscript_id=payload.manuscript_id,
            format=payload.format,
            state=state,
            output_artifact_id=output_artifact_id,
            requested_by=self.repository.principal_id,
            requested_at=now,
            completed_at=completed_at,
        )
        self.repository.store.export_jobs[export_job.id] = export_job
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="export.job.created",
            target_kind=LineageKind.EXPORT_JOB,
            target_id=export_job.id,
            payload_json={
                "manuscript_id": str(payload.manuscript_id),
                "format": payload.format.value,
                "state": export_job.state.value,
                "blocking_reasons": blocking_reasons,
                "output_artifact_id": str(output_artifact_id) if output_artifact_id else None,
            },
        )
        if export_job.state == ExportState.COMPLETED and output_artifact_id is not None and export_job.completed_at is not None:
            append_audit_event(
                self.repository.store,
                project_id=project_id,
                event_type="export.completed",
                target_kind=LineageKind.EXPORT_JOB,
                target_id=export_job.id,
                payload_json={
                    "export_job_id": str(export_job.id),
                    "manuscript_id": str(export_job.manuscript_id),
                    "output_artifact_id": str(output_artifact_id),
                    "format": export_job.format.value,
                    "completed_at": export_job.completed_at.isoformat(),
                },
            )
        return CreateExportJobResponse(export_job=export_job)

    def get_export_job(self, project_id: UUID, export_job_id: UUID) -> ExportJobDetailResponse:
        self._require_project(project_id, "exports:read")
        export_job = self.repository.require_project_scoped(
            "export_jobs",
            project_id,
            export_job_id,
            "export job",
            required_scopes=("exports:read",),
        )
        output_artifact = (
            self.repository.store.artifacts.get(export_job.output_artifact_id)
            if export_job.output_artifact_id is not None
            else None
        )
        return ExportJobDetailResponse(export_job=export_job, output_artifact=output_artifact)

    def list_export_jobs(self, project_id: UUID, *, limit: int, offset: int) -> ExportJobListResponse:
        self._require_project(project_id, "exports:read")
        export_jobs = sorted(
            [
                export_job
                for export_job in self.repository.store.export_jobs.values()
                if export_job.project_id == project_id
            ],
            key=lambda export_job: export_job.requested_at,
            reverse=True,
        )
        return ExportJobListResponse(items=self.paginate(export_jobs, limit=limit, offset=offset))

    def _require_project(self, project_id: UUID, *required_scopes: str) -> None:
        self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_manuscript(self, project_id: UUID, manuscript_id: UUID, *required_scopes: str) -> ManuscriptRead:
        return self.repository.require_project_scoped(
            "manuscripts",
            project_id,
            manuscript_id,
            "manuscript",
            required_scopes=tuple(required_scopes),
        )

    def _collect_blocking_reasons(self, project_id: UUID, manuscript: ManuscriptRead) -> list[str]:
        verification = self.repository.store.manuscript_verifications.get((manuscript.id, manuscript.current_version_no))
        blocks = [
            block
            for block in self.repository.store.manuscript_blocks.values()
            if block.project_id == project_id
            and block.manuscript_id == manuscript.id
            and block.version_no == manuscript.current_version_no
        ]
        blocking_reasons: list[str] = []
        if verification is None:
            blocking_reasons.append("manuscript_version_not_verified")
        else:
            blocking_reasons.extend(verification.blocking_summary)
            if any(evaluation.status != GateStatus.PASSED for evaluation in verification.gate_evaluations):
                blocking_reasons.append("manuscript_version_has_blocking_gate")
        if not blocks:
            blocking_reasons.append("manuscript_has_no_blocks")
        for block in blocks:
            if not block.assertion_ids:
                blocking_reasons.append(f"block {block.id} missing assertion_ids")
                continue
            for assertion_id in block.assertion_ids:
                assertion = self.repository.store.assertions.get(assertion_id)
                if assertion is None or assertion.project_id != project_id:
                    blocking_reasons.append(f"assertion {assertion_id} not found")
                    continue
                if assertion.state != AssertionState.VERIFIED:
                    blocking_reasons.append(f"assertion {assertion_id} is not verified")
                    continue
                if (block.id, assertion_id) not in self.repository.store.block_assertion_links:
                    blocking_reasons.append(f"block {block.id} missing block_assertion_link for {assertion_id}")
        return list(dict.fromkeys(blocking_reasons))

    def _build_output_artifact(
        self,
        project_id: UUID,
        manuscript: ManuscriptRead,
        export_format: str,
        now,
    ) -> ArtifactRead:
        artifact_type_map = {
            "docx": ArtifactType.DOCX,
            "pdf": ArtifactType.PDF,
            "zip": ArtifactType.ZIP,
        }
        mime_type_map = {
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pdf": "application/pdf",
            "zip": "application/zip",
        }
        rendered_content = f"{manuscript.title}:{manuscript.current_version_no}:{export_format}"
        rendered_bytes = rendered_content.encode("utf-8")
        object_key = build_export_object_key(manuscript.id, export_format)
        storage_uri = storage_uri_for_key(object_key)
        write_object_bytes(object_key, rendered_bytes)
        return ArtifactRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            run_id=None,
            artifact_type=artifact_type_map[export_format],
            output_slot=None,
            storage_uri=storage_uri,
            mime_type=mime_type_map[export_format],
            sha256=sha256(rendered_bytes).hexdigest(),
            size_bytes=len(rendered_bytes),
            metadata_json={
                "manuscript_id": str(manuscript.id),
                "version_no": manuscript.current_version_no,
                "export_format": export_format,
            },
            superseded_by=None,
            created_at=now,
        )
