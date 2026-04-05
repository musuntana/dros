from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import AsyncIterator
from uuid import UUID

from fastapi import HTTPException, Request, status

from ..auth import auth_context_to_scopes_json
from ..object_store import build_upload_object_key, normalize_object_key, object_key_to_path, resolve_storage_uri
from ..repositories.base import append_audit_event
from ..schemas.api import (
    SessionRead,
    SignedArtifactUrlResponse,
    SignedUploadRequest,
    SignedUploadResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
)
from ..schemas.domain import ArtifactRead, AuditEventRead
from ..schemas.enums import LineageKind
from ..schemas.events import (
    AnalysisRunFailedEvent,
    AnalysisRunRequestedEvent,
    AnalysisRunSucceededEvent,
    ArtifactCreatedEvent,
    DatasetSnapshotCreatedEvent,
    ExportCompletedEvent,
    ProjectCreatedEvent,
    ReviewCompletedEvent,
    ReviewRequestedEvent,
    WorkflowStartedEvent,
)
from .base import BaseService

SIGNED_URL_TTL_SECONDS = 900
EVENT_POLL_INTERVAL_SECONDS = 1.0


@dataclass(slots=True)
class GatewayService(BaseService):
    repository: object

    def get_session(self) -> SessionRead:
        return SessionRead(
            actor_id=str(self.repository.actor_id),
            principal_id=str(self.repository.principal_id),
            tenant_id=str(self.repository.tenant_id),
            scopes_json=auth_context_to_scopes_json(self.repository.auth_context),
        )

    def sign_upload(self, payload: SignedUploadRequest) -> SignedUploadResponse:
        self.require_scopes("uploads:write")
        object_key = build_upload_object_key(payload.filename)
        upload_path = object_key_to_path(object_key)
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        return SignedUploadResponse(
            upload_url=upload_path.resolve().as_uri(),
            object_key=object_key,
            expires_in_seconds=SIGNED_URL_TTL_SECONDS,
        )

    def complete_upload(self, payload: UploadCompleteRequest) -> UploadCompleteResponse:
        self.require_scopes("uploads:write")
        try:
            object_key = normalize_object_key(payload.object_key)
            upload_path = object_key_to_path(object_key)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

        if not upload_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"uploaded object {object_key} not found")

        digest = sha256(upload_path.read_bytes()).hexdigest()
        if digest != payload.sha256:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="sha256 mismatch for uploaded object")

        append_audit_event(
            self.repository.store,
            project_id=None,
            event_type="client.upload.completed",
            target_kind=LineageKind.PROJECT,
            target_id=None,
            payload_json={"object_key": object_key, "sha256": payload.sha256},
        )
        return UploadCompleteResponse(file_ref=object_key)

    def get_artifact_download_url(self, project_id: UUID, artifact_id: UUID) -> SignedArtifactUrlResponse:
        self._require_project(project_id, "downloads:read")
        artifact = self._require_artifact(project_id, artifact_id, "downloads:read")
        resolved_path = resolve_storage_uri(artifact.storage_uri)
        if resolved_path is None or not resolved_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"artifact {artifact_id} has no downloadable payload",
            )

        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="artifact.download_url.issued",
            target_kind=LineageKind.ARTIFACT,
            target_id=artifact.id,
            payload_json={"storage_uri": artifact.storage_uri},
        )
        return SignedArtifactUrlResponse(
            download_url=resolved_path.resolve().as_uri(),
            expires_in_seconds=SIGNED_URL_TTL_SECONDS,
        )

    async def stream_project_events(self, project_id: UUID, request: Request, *, once: bool = False) -> AsyncIterator[str]:
        yielded_event_ids: set[UUID] = set()

        while True:
            if await request.is_disconnected():
                break

            project_events = [
                event
                for event in self.repository.store.audit_events.values()
                if event.project_id == project_id and event.id not in yielded_event_ids
            ]
            project_events.sort(key=lambda event: event.created_at)

            if project_events:
                for event in project_events:
                    yielded_event_ids.add(event.id)
                    payload = self._serialize_project_event(event)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield ": keepalive\n\n"

            if once:
                break

            await asyncio.sleep(EVENT_POLL_INTERVAL_SECONDS)

    def authorize_project_events(self, project_id: UUID) -> None:
        self._require_project(project_id, "events:read")

    def _require_project(self, project_id: UUID, *required_scopes: str) -> None:
        self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_artifact(self, project_id: UUID, artifact_id: UUID, *required_scopes: str) -> ArtifactRead:
        return self.repository.require_project_scoped(
            "artifacts",
            project_id,
            artifact_id,
            "artifact",
            required_scopes=tuple(required_scopes),
        )

    def _serialize_project_event(self, event: AuditEventRead) -> dict[str, object]:
        structured = self._serialize_structured_event(event)
        if structured is not None:
            return structured
        return {
            "event_id": str(event.id),
            "event_name": event.event_type,
            "schema_version": "1.0.0",
            "produced_by": "gateway.sse",
            "trace_id": event.trace_id or f"audit:{event.id}",
            "request_id": event.request_id or str(event.id),
            "tenant_id": str(event.tenant_id),
            "project_id": str(event.project_id) if event.project_id is not None else "",
            "idempotency_key": event.event_hash,
            "occurred_at": event.created_at.isoformat(),
            "payload": event.payload_json,
        }

    def _serialize_structured_event(self, event: AuditEventRead) -> dict[str, object] | None:
        builders = {
            "project.created": self._build_project_created_event,
            "dataset.snapshot.created": self._build_dataset_snapshot_created_event,
            "workflow.started": self._build_workflow_started_event,
            "analysis.run.requested": self._build_analysis_run_requested_event,
            "analysis.run.succeeded": self._build_analysis_run_succeeded_event,
            "analysis.run.failed": self._build_analysis_run_failed_event,
            "artifact.created": self._build_artifact_created_event,
            "review.requested": self._build_review_requested_event,
            "review.completed": self._build_review_completed_event,
            "export.completed": self._build_export_completed_event,
        }
        builder = builders.get(event.event_type)
        if builder is None:
            return None
        return builder(event)

    def _build_project_created_event(self, event: AuditEventRead) -> dict[str, object]:
        project = self.repository.store.projects.get(event.target_id)
        if project is None:
            return self._fallback_structured_event(event)
        return ProjectCreatedEvent(
            **self._event_envelope(event, produced_by="project_service", idempotency_key=str(project.id)),
            payload={
                "project_id": project.id,
                "owner_id": project.owner_id,
                "project_type": project.project_type.value,
                "status": project.status.value,
            },
        ).model_dump(mode="json")

    def _build_dataset_snapshot_created_event(self, event: AuditEventRead) -> dict[str, object]:
        snapshot = self.repository.store.dataset_snapshots.get(event.target_id)
        if snapshot is None:
            return self._fallback_structured_event(event)
        dataset = self.repository.store.datasets.get(snapshot.dataset_id)
        if dataset is None:
            return self._fallback_structured_event(event)
        return DatasetSnapshotCreatedEvent(
            **self._event_envelope(event, produced_by="dataset_service", idempotency_key=str(snapshot.id)),
            payload={
                "dataset_id": snapshot.dataset_id,
                "snapshot_id": snapshot.id,
                "snapshot_no": snapshot.snapshot_no,
                "source_kind": dataset.source_kind.value,
                "input_hash_sha256": snapshot.input_hash_sha256,
                "deid_status": snapshot.deid_status.value,
                "phi_scan_status": snapshot.phi_scan_status.value,
            },
        ).model_dump(mode="json")

    def _build_workflow_started_event(self, event: AuditEventRead) -> dict[str, object]:
        workflow = self.repository.store.workflow_instances.get(event.target_id)
        if workflow is None:
            return self._fallback_structured_event(event)
        return WorkflowStartedEvent(
            **self._event_envelope(event, produced_by="workflow_service", idempotency_key=str(workflow.id)),
            payload={
                "workflow_instance_id": workflow.id,
                "workflow_type": workflow.workflow_type,
                "runtime_backend": workflow.runtime_backend.value,
                "state": workflow.state.value,
                "input_refs": [],
            },
        ).model_dump(mode="json")

    def _build_analysis_run_requested_event(self, event: AuditEventRead) -> dict[str, object]:
        run = self.repository.store.analysis_runs.get(event.target_id)
        if run is None:
            return self._fallback_structured_event(event)
        return AnalysisRunRequestedEvent(
            **self._event_envelope(event, produced_by="workflow_service", idempotency_key=str(run.id)),
            payload={
                "analysis_run_id": run.id,
                "workflow_instance_id": run.workflow_instance_id,
                "snapshot_id": run.snapshot_id,
                "template_id": run.template_id,
                "repro_fingerprint": run.repro_fingerprint,
            },
        ).model_dump(mode="json")

    def _build_analysis_run_succeeded_event(self, event: AuditEventRead) -> dict[str, object]:
        run = self.repository.store.analysis_runs.get(event.target_id)
        if run is None or run.finished_at is None:
            return self._fallback_structured_event(event)
        artifact_ids = [
            artifact.id
            for artifact in self.repository.store.artifacts.values()
            if artifact.project_id == run.project_id and artifact.run_id == run.id
        ]
        artifact_ids.sort(key=str)
        return AnalysisRunSucceededEvent(
            **self._event_envelope(event, produced_by="runner", idempotency_key=str(run.id)),
            payload={
                "analysis_run_id": run.id,
                "workflow_instance_id": run.workflow_instance_id,
                "artifact_ids": artifact_ids,
                "output_artifact_count": len(artifact_ids),
                "finished_at": run.finished_at,
            },
        ).model_dump(mode="json")

    def _build_analysis_run_failed_event(self, event: AuditEventRead) -> dict[str, object]:
        run = self.repository.store.analysis_runs.get(event.target_id)
        if run is None:
            return self._fallback_structured_event(event)
        exit_code = run.exit_code if run.exit_code is not None else "unknown"
        return AnalysisRunFailedEvent(
            **self._event_envelope(event, produced_by="runner", idempotency_key=f"{run.id}:{exit_code}"),
            payload={
                "analysis_run_id": run.id,
                "workflow_instance_id": run.workflow_instance_id,
                "exit_code": run.exit_code,
                "error_class": run.error_class,
                "error_message_trunc": run.error_message_trunc,
            },
        ).model_dump(mode="json")

    def _build_artifact_created_event(self, event: AuditEventRead) -> dict[str, object]:
        artifact = self.repository.store.artifacts.get(event.target_id)
        if artifact is None:
            return self._fallback_structured_event(event)
        return ArtifactCreatedEvent(
            **self._event_envelope(event, produced_by="artifact_service", idempotency_key=str(artifact.id)),
            payload={
                "artifact_id": artifact.id,
                "run_id": artifact.run_id,
                "artifact_type": artifact.artifact_type.value,
                "storage_uri": artifact.storage_uri,
                "sha256": artifact.sha256,
            },
        ).model_dump(mode="json")

    def _build_review_requested_event(self, event: AuditEventRead) -> dict[str, object]:
        review = self.repository.store.reviews.get(event.target_id)
        if review is None:
            return self._fallback_structured_event(event)
        return ReviewRequestedEvent(
            **self._event_envelope(event, produced_by="review_service", idempotency_key=str(review.id)),
            payload={
                "review_id": review.id,
                "review_type": review.review_type.value,
                "target_kind": review.target_kind.value,
                "target_id": review.target_id,
                "state": review.state.value,
            },
        ).model_dump(mode="json")

    def _build_review_completed_event(self, event: AuditEventRead) -> dict[str, object]:
        review = self.repository.store.reviews.get(event.target_id)
        if review is None:
            return self._fallback_structured_event(event)
        return ReviewCompletedEvent(
            **self._event_envelope(event, produced_by="review_service", idempotency_key=str(review.id)),
            payload={
                "review_id": review.id,
                "review_type": review.review_type.value,
                "target_kind": review.target_kind.value,
                "target_id": review.target_id,
                "state": review.state.value,
                "reviewer_id": review.reviewer_id,
                "decided_at": review.decided_at,
            },
        ).model_dump(mode="json")

    def _build_export_completed_event(self, event: AuditEventRead) -> dict[str, object]:
        export_job = self.repository.store.export_jobs.get(event.target_id)
        if export_job is None or export_job.output_artifact_id is None or export_job.completed_at is None:
            return self._fallback_structured_event(event)
        return ExportCompletedEvent(
            **self._event_envelope(event, produced_by="export_service", idempotency_key=str(export_job.id)),
            payload={
                "export_job_id": export_job.id,
                "manuscript_id": export_job.manuscript_id,
                "output_artifact_id": export_job.output_artifact_id,
                "format": export_job.format.value,
                "completed_at": export_job.completed_at,
            },
        ).model_dump(mode="json")

    def _event_envelope(self, event: AuditEventRead, *, produced_by: str, idempotency_key: str) -> dict[str, object]:
        return {
            "event_id": event.id,
            "schema_version": "1.0.0",
            "produced_by": produced_by,
            "trace_id": event.trace_id or f"{event.event_type}:{event.id}",
            "request_id": event.request_id or str(event.id),
            "tenant_id": event.tenant_id,
            "project_id": event.project_id,
            "idempotency_key": idempotency_key,
            "occurred_at": event.created_at,
        }

    def _fallback_structured_event(self, event: AuditEventRead) -> dict[str, object]:
        return {
            "event_id": str(event.id),
            "event_name": event.event_type,
            "schema_version": "1.0.0",
            "produced_by": "gateway.sse",
            "trace_id": event.trace_id or f"audit:{event.id}",
            "request_id": event.request_id or str(event.id),
            "tenant_id": str(event.tenant_id),
            "project_id": str(event.project_id) if event.project_id is not None else "",
            "idempotency_key": event.event_hash,
            "occurred_at": event.created_at.isoformat(),
            "payload": event.payload_json,
        }
