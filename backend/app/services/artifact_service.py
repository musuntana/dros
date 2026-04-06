from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.artifact_repository import ArtifactRepository
from ..schemas.api import (
    ArtifactDetailResponse,
    ArtifactListResponse,
    CreateArtifactRequest,
    CreateArtifactResponse,
    CreateLineageEdgeRequest,
    CreateLineageEdgeResponse,
    LineageQueryResponse,
)
from ..schemas.domain import ArtifactRead, LineageEdgeRead
from ..schemas.enums import LineageEdgeType, LineageKind
from .base import BaseService


@dataclass(slots=True)
class ArtifactService(BaseService):
    repository: ArtifactRepository

    def create_artifact(self, project_id: UUID, payload: CreateArtifactRequest) -> CreateArtifactResponse:
        self._require_project(project_id, "artifacts:write")
        resolved_output_slot = self._resolve_output_slot(payload.output_slot, payload.metadata_json)
        normalized_metadata_json = self._normalize_metadata_json(payload.metadata_json, resolved_output_slot)
        if payload.run_id is not None:
            self._require_analysis_run(project_id, payload.run_id, "artifacts:write")

        artifact = ArtifactRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            run_id=payload.run_id,
            artifact_type=payload.artifact_type,
            output_slot=resolved_output_slot,
            storage_uri=payload.storage_uri,
            mime_type=payload.mime_type,
            sha256=payload.sha256,
            size_bytes=payload.size_bytes,
            metadata_json=normalized_metadata_json,
            superseded_by=None,
            created_at=self.now(),
        )

        with self.repository.unit_of_work() as uow:
            if payload.run_id is not None and resolved_output_slot is not None:
                if self.repository.check_output_slot_exists(
                    uow,
                    project_id=project_id,
                    run_id=payload.run_id,
                    artifact_type=payload.artifact_type,
                    output_slot=resolved_output_slot,
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"artifact output_slot {resolved_output_slot} already exists for run {payload.run_id} "
                            f"and artifact_type {payload.artifact_type.value}"
                        ),
                    )

            self.repository.insert_artifact(uow, artifact)

            if payload.run_id is not None:
                edge = LineageEdgeRead(
                    id=uuid4(),
                    tenant_id=self.repository.tenant_id,
                    project_id=project_id,
                    from_kind=LineageKind.ANALYSIS_RUN,
                    from_id=payload.run_id,
                    edge_type=LineageEdgeType.EMITS,
                    to_kind=LineageKind.ARTIFACT,
                    to_id=artifact.id,
                    created_at=self.now(),
                )
                self.repository.insert_lineage_edge(uow, edge)

            self.repository.append_audit_event_uow(
                uow,
                project_id=project_id,
                event_type="artifact.created",
                target_kind=LineageKind.ARTIFACT,
                target_id=artifact.id,
                payload_json={
                    "run_id": str(payload.run_id) if payload.run_id else None,
                    "artifact_type": payload.artifact_type.value,
                    "output_slot": resolved_output_slot,
                },
            )

        return CreateArtifactResponse(artifact=artifact)

    def list_artifacts(self, project_id: UUID, *, limit: int, offset: int) -> ArtifactListResponse:
        self._require_project(project_id, "artifacts:read")
        with self.repository.unit_of_work() as uow:
            all_artifacts = self.repository.list_artifacts(
                uow, project_id, limit=None, offset=None,
            )
        return ArtifactListResponse(items=self.paginate(all_artifacts, limit=limit, offset=offset))

    def get_artifact(self, project_id: UUID, artifact_id: UUID) -> ArtifactDetailResponse:
        artifact = self._require_artifact(project_id, artifact_id, "artifacts:read")
        return ArtifactDetailResponse(artifact=artifact)

    def create_lineage_edge(self, project_id: UUID, payload: CreateLineageEdgeRequest) -> CreateLineageEdgeResponse:
        self._require_project(project_id, "artifacts:write")
        self._require_lineage_node(project_id, payload.from_kind, payload.from_id, "artifacts:write")
        self._require_lineage_node(project_id, payload.to_kind, payload.to_id, "artifacts:write")
        if payload.edge_type == LineageEdgeType.SUPERSEDES and payload.from_id == payload.to_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="supersedes edge requires distinct from_id and to_id",
            )
        if (
            payload.edge_type == LineageEdgeType.SUPERSEDES
            and payload.from_kind == LineageKind.ARTIFACT
            and payload.to_kind == LineageKind.ARTIFACT
        ):
            superseded_artifact = self._require_artifact(project_id, payload.from_id, "artifacts:write")
            replacement_artifact = self._require_artifact(project_id, payload.to_id, "artifacts:write")
            if superseded_artifact.superseded_by is not None and superseded_artifact.superseded_by != payload.to_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"artifact {payload.from_id} already superseded by {superseded_artifact.superseded_by}",
                )
            self._validate_artifact_supersedes_pair(
                project_id=project_id,
                superseded_artifact=superseded_artifact,
                replacement_artifact=replacement_artifact,
            )

        edge = LineageEdgeRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            from_kind=payload.from_kind,
            from_id=payload.from_id,
            edge_type=payload.edge_type,
            to_kind=payload.to_kind,
            to_id=payload.to_id,
            created_at=self.now(),
        )

        with self.repository.unit_of_work() as uow:
            self.repository.insert_lineage_edge(uow, edge)
            if (
                payload.edge_type == LineageEdgeType.SUPERSEDES
                and payload.from_kind == LineageKind.ARTIFACT
                and payload.to_kind == LineageKind.ARTIFACT
            ):
                self.repository.update_superseded_by(uow, superseded_artifact.id, payload.to_id)
            self.repository.append_audit_event_uow(
                uow,
                project_id=project_id,
                event_type="lineage.edge.created",
                target_kind=payload.to_kind,
                target_id=payload.to_id,
                payload_json=payload.model_dump(),
            )

        return CreateLineageEdgeResponse(edge=edge)

    def _validate_artifact_supersedes_pair(
        self,
        *,
        project_id: UUID,
        superseded_artifact: ArtifactRead,
        replacement_artifact: ArtifactRead,
    ) -> None:
        if superseded_artifact.artifact_type != replacement_artifact.artifact_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "artifact supersedes requires matching artifact_type; "
                    f"got {superseded_artifact.artifact_type.value} -> {replacement_artifact.artifact_type.value}"
                ),
            )

        superseded_output_slot = superseded_artifact.output_slot
        replacement_output_slot = replacement_artifact.output_slot
        if superseded_output_slot is None or replacement_output_slot is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="artifact supersedes requires both artifacts to declare output_slot",
            )
        if superseded_output_slot != replacement_output_slot:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "artifact supersedes requires matching output_slot; "
                    f"got {superseded_output_slot} -> {replacement_output_slot}"
                ),
            )

        if superseded_artifact.run_id is None or replacement_artifact.run_id is None:
            return
        replacement_run = self._require_analysis_run(project_id, replacement_artifact.run_id, "artifacts:write")
        if replacement_run.rerun_of_run_id != superseded_artifact.run_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "artifact supersedes for run-backed artifacts requires replacement run to declare "
                    f"rerun_of_run_id={superseded_artifact.run_id}"
                ),
            )

    def _resolve_output_slot(self, output_slot: str | None, metadata_json: dict[str, object]) -> str | None:
        metadata_output_slot = metadata_json.get("output_slot")
        if output_slot is not None and metadata_output_slot is not None and str(metadata_output_slot) != output_slot:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "artifact output_slot mismatch between top-level field and metadata_json.output_slot; "
                    f"got {output_slot} vs {metadata_output_slot}"
                ),
            )
        if output_slot is not None:
            return output_slot
        if metadata_output_slot is not None:
            return str(metadata_output_slot)
        return None

    def _normalize_metadata_json(self, metadata_json: dict[str, object], output_slot: str | None) -> dict[str, object]:
        normalized = dict(metadata_json)
        if output_slot is not None:
            normalized["output_slot"] = output_slot
        return normalized

    def get_lineage(self, project_id: UUID) -> LineageQueryResponse:
        self._require_project(project_id, "artifacts:read")
        with self.repository.unit_of_work() as uow:
            edges, artifacts, assertions, analysis_runs = self.repository.get_lineage_data(uow, project_id)
        return LineageQueryResponse(
            project_id=project_id,
            edges=edges,
            artifacts=artifacts,
            assertions=assertions,
            analysis_runs=analysis_runs,
        )

    def _require_project(self, project_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_analysis_run(self, project_id: UUID, run_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project_scoped(
            "analysis_runs",
            project_id,
            run_id,
            "analysis run",
            required_scopes=tuple(required_scopes),
        )

    def _require_artifact(self, project_id: UUID, artifact_id: UUID, *required_scopes: str) -> ArtifactRead:
        return self.repository.require_project_scoped(
            "artifacts",
            project_id,
            artifact_id,
            "artifact",
            required_scopes=tuple(required_scopes),
        )

    def _require_lineage_node(self, project_id: UUID, kind: LineageKind, node_id: UUID, *required_scopes: str) -> object:
        self.repository.require_project(project_id, required_scopes=tuple(required_scopes))
        store = self.repository.store
        project_scoped = {
            LineageKind.PROJECT: store.projects,
            LineageKind.DATASET: store.datasets,
            LineageKind.DATASET_SNAPSHOT: store.dataset_snapshots,
            LineageKind.WORKFLOW_INSTANCE: store.workflow_instances,
            LineageKind.WORKFLOW_TASK: store.workflow_tasks,
            LineageKind.ANALYSIS_RUN: store.analysis_runs,
            LineageKind.ARTIFACT: store.artifacts,
            LineageKind.ASSERTION: store.assertions,
            LineageKind.MANUSCRIPT: store.manuscripts,
            LineageKind.MANUSCRIPT_BLOCK: store.manuscript_blocks,
            LineageKind.REVIEW: store.reviews,
            LineageKind.EXPORT_JOB: store.export_jobs,
        }
        if kind in project_scoped:
            store_name_map = {
                LineageKind.PROJECT: "projects",
                LineageKind.DATASET: "datasets",
                LineageKind.DATASET_SNAPSHOT: "dataset_snapshots",
                LineageKind.WORKFLOW_INSTANCE: "workflow_instances",
                LineageKind.WORKFLOW_TASK: "workflow_tasks",
                LineageKind.ANALYSIS_RUN: "analysis_runs",
                LineageKind.ARTIFACT: "artifacts",
                LineageKind.ASSERTION: "assertions",
                LineageKind.MANUSCRIPT: "manuscripts",
                LineageKind.MANUSCRIPT_BLOCK: "manuscript_blocks",
                LineageKind.REVIEW: "reviews",
                LineageKind.EXPORT_JOB: "export_jobs",
            }
            if kind == LineageKind.PROJECT:
                return self.repository.require_project(node_id, required_scopes=tuple(required_scopes))
            return self.repository.require_project_scoped(
                store_name_map[kind],
                project_id,
                node_id,
                kind.value,
                required_scopes=tuple(required_scopes),
            )

        global_scoped = {
            LineageKind.EVIDENCE_SOURCE: store.evidence_sources,
            LineageKind.EVIDENCE_CHUNK: store.evidence_chunks,
            LineageKind.ANALYSIS_TEMPLATE: store.analysis_templates,
        }
        if kind in global_scoped:
            item = global_scoped[kind].get(node_id)
            if item is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind.value} {node_id} not found")
            return item

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"unsupported lineage kind for project route: {kind.value}",
        )
