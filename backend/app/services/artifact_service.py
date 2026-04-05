from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.base import append_audit_event
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
    repository: object

    def create_artifact(self, project_id: UUID, payload: CreateArtifactRequest) -> CreateArtifactResponse:
        self._require_project(project_id, "artifacts:write")
        if payload.run_id is not None:
            self._require_analysis_run(project_id, payload.run_id, "artifacts:write")

        artifact = ArtifactRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            run_id=payload.run_id,
            artifact_type=payload.artifact_type,
            storage_uri=payload.storage_uri,
            mime_type=payload.mime_type,
            sha256=payload.sha256,
            size_bytes=payload.size_bytes,
            metadata_json=payload.metadata_json,
            superseded_by=None,
            created_at=self.now(),
        )
        self.repository.store.artifacts[artifact.id] = artifact

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
            self.repository.store.lineage_edges[edge.id] = edge

        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="artifact.created",
            target_kind=LineageKind.ARTIFACT,
            target_id=artifact.id,
            payload_json={"run_id": str(payload.run_id) if payload.run_id else None, "artifact_type": payload.artifact_type.value},
        )
        return CreateArtifactResponse(artifact=artifact)

    def list_artifacts(self, project_id: UUID, *, limit: int, offset: int) -> ArtifactListResponse:
        self._require_project(project_id, "artifacts:read")
        artifacts = sorted(
            [
                artifact
                for artifact in self.repository.store.artifacts.values()
                if artifact.project_id == project_id
            ],
            key=lambda artifact: artifact.created_at,
            reverse=True,
        )
        return ArtifactListResponse(items=self.paginate(artifacts, limit=limit, offset=offset))

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
            if superseded_artifact.superseded_by is not None and superseded_artifact.superseded_by != payload.to_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"artifact {payload.from_id} already superseded by {superseded_artifact.superseded_by}",
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
        self.repository.store.lineage_edges[edge.id] = edge
        if (
            payload.edge_type == LineageEdgeType.SUPERSEDES
            and payload.from_kind == LineageKind.ARTIFACT
            and payload.to_kind == LineageKind.ARTIFACT
        ):
            self.repository.store.artifacts[superseded_artifact.id] = superseded_artifact.model_copy(
                update={"superseded_by": payload.to_id}
            )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="lineage.edge.created",
            target_kind=payload.to_kind,
            target_id=payload.to_id,
            payload_json=payload.model_dump(),
        )
        return CreateLineageEdgeResponse(edge=edge)

    def get_lineage(self, project_id: UUID) -> LineageQueryResponse:
        self._require_project(project_id, "artifacts:read")
        edges = [
            edge
            for edge in self.repository.store.lineage_edges.values()
            if edge.project_id == project_id
        ]
        edges.sort(key=lambda edge: edge.created_at)
        artifacts = [
            artifact
            for artifact in self.repository.store.artifacts.values()
            if artifact.project_id == project_id
        ]
        artifacts.sort(key=lambda artifact: artifact.created_at)
        assertions = [
            assertion
            for assertion in self.repository.store.assertions.values()
            if assertion.project_id == project_id
        ]
        assertions.sort(key=lambda assertion: assertion.created_at)
        analysis_runs = [
            run
            for run in self.repository.store.analysis_runs.values()
            if run.project_id == project_id
        ]
        analysis_runs.sort(key=lambda run: run.created_at)
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
