from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from ..schemas.domain import (
    AnalysisRunRead,
    ArtifactRead,
    AssertionRead,
    LineageEdgeRead,
)
from ..schemas.enums import ArtifactType
from .base import BaseRepository


class ArtifactRepository(BaseRepository):
    """Owns artifact metadata and explicit lineage edges."""

    store_names = ("artifacts", "lineage_edges")

    # ------------------------------------------------------------------
    # Artifact CRUD
    # ------------------------------------------------------------------

    def insert_artifact(self, uow, artifact: ArtifactRead) -> None:
        if self.is_rowlevel:
            from ..db.fk_sync import ensure_artifact_parents
            from ..db.query import insert_row

            ensure_artifact_parents(
                uow.conn, self.store,
                project_id=artifact.project_id,
                run_id=artifact.run_id,
            )
            insert_row(uow.conn, "artifacts", _artifact_to_row(artifact))
        else:
            self.store.artifacts[artifact.id] = artifact

    def get_artifact(self, uow, project_id: UUID, artifact_id: UUID) -> ArtifactRead | None:
        if self.is_rowlevel:
            from ..db.query import select_by_id

            row = select_by_id(uow.conn, "artifacts", artifact_id)
            if row is None or row["project_id"] != project_id:
                return None
            return _row_to_artifact(row)
        item = self.store.artifacts.get(artifact_id)
        if item is None or item.project_id != project_id:
            return None
        return item

    def list_artifacts(
        self, uow, project_id: UUID, *, limit: int | None = None, offset: int | None = None
    ) -> list[ArtifactRead]:
        if self.is_rowlevel:
            from ..db.query import select_where

            rows = select_where(
                uow.conn,
                "artifacts",
                {"project_id": project_id},
                order_by="created_at",
                order_desc=True,
                limit=limit,
                offset=offset,
            )
            return [_row_to_artifact(r) for r in rows]
        artifacts = sorted(
            [a for a in self.store.artifacts.values() if a.project_id == project_id],
            key=lambda a: a.created_at,
            reverse=True,
        )
        start = offset or 0
        if limit is not None:
            return artifacts[start : start + limit]
        return artifacts[start:]

    def check_output_slot_exists(
        self,
        uow,
        *,
        project_id: UUID,
        run_id: UUID,
        artifact_type: ArtifactType,
        output_slot: str,
    ) -> bool:
        if self.is_rowlevel:
            from ..db.query import exists_where

            return exists_where(uow.conn, "artifacts", {
                "project_id": project_id,
                "run_id": run_id,
                "artifact_type": artifact_type.value,
                "output_slot": output_slot,
            })
        for artifact in self.store.artifacts.values():
            if artifact.project_id != project_id or artifact.run_id != run_id:
                continue
            if artifact.artifact_type != artifact_type:
                continue
            if artifact.output_slot == output_slot:
                return True
        return False

    def list_unsuperseded_by_run(
        self, uow, project_id: UUID, run_id: UUID
    ) -> list[ArtifactRead]:
        """Return artifacts for a specific run that have not been superseded."""
        if self.is_rowlevel:
            from ..db.query import select_where

            rows = select_where(
                uow.conn,
                "artifacts",
                {"project_id": project_id, "run_id": run_id},
                order_by="created_at",
                order_desc=False,
            )
            return [_row_to_artifact(r) for r in rows if r["superseded_by"] is None]
        return sorted(
            [
                a for a in self.store.artifacts.values()
                if a.project_id == project_id
                and a.run_id == run_id
                and a.superseded_by is None
            ],
            key=lambda a: a.created_at,
        )

    def update_superseded_by(self, uow, artifact_id: UUID, superseded_by: UUID) -> None:
        if self.is_rowlevel:
            from ..db.query import update_columns

            update_columns(uow.conn, "artifacts", artifact_id, {"superseded_by": superseded_by})
        else:
            artifact = self.store.artifacts[artifact_id]
            self.store.artifacts[artifact_id] = artifact.model_copy(
                update={"superseded_by": superseded_by}
            )

    # ------------------------------------------------------------------
    # Lineage edges
    # ------------------------------------------------------------------

    def insert_lineage_edge(self, uow, edge: LineageEdgeRead) -> None:
        if self.is_rowlevel:
            from ..db.fk_sync import ensure_project
            from ..db.query import insert_row

            ensure_project(uow.conn, self.store, edge.project_id)
            insert_row(uow.conn, "lineage_edges", _edge_to_row(edge))
        else:
            self.store.lineage_edges[edge.id] = edge

    def list_lineage_edges(self, uow, project_id: UUID) -> list[LineageEdgeRead]:
        if self.is_rowlevel:
            from ..db.query import select_where

            rows = select_where(
                uow.conn,
                "lineage_edges",
                {"project_id": project_id},
                order_by="created_at",
                order_desc=False,
            )
            return [_row_to_edge(r) for r in rows]
        edges = [e for e in self.store.lineage_edges.values() if e.project_id == project_id]
        edges.sort(key=lambda e: e.created_at)
        return edges

    # ------------------------------------------------------------------
    # Lineage query (cross-boundary: artifacts + edges + assertions + runs)
    # ------------------------------------------------------------------

    def get_lineage_data(
        self, uow, project_id: UUID
    ) -> tuple[
        list[LineageEdgeRead],
        list[ArtifactRead],
        list[AssertionRead],
        list[AnalysisRunRead],
    ]:
        """Return (edges, artifacts, assertions, analysis_runs) for a project."""
        if self.is_rowlevel:
            from ..db.fk_sync import ensure_project_analysis_runs
            from ..db.query import select_where

            ensure_project_analysis_runs(uow.conn, self.store, project_id)
            edge_rows = select_where(
                uow.conn, "lineage_edges", {"project_id": project_id},
                order_by="created_at", order_desc=False,
            )
            artifact_rows = select_where(
                uow.conn, "artifacts", {"project_id": project_id},
                order_by="created_at", order_desc=False,
            )
            assertion_rows = select_where(
                uow.conn, "assertions", {"project_id": project_id},
                order_by="created_at", order_desc=False,
            )
            run_rows = select_where(
                uow.conn, "analysis_runs", {"project_id": project_id},
                order_by="created_at", order_desc=False,
            )
            return (
                [_row_to_edge(r) for r in edge_rows],
                [_row_to_artifact(r) for r in artifact_rows],
                [AssertionRead.model_validate(r) for r in assertion_rows],
                [AnalysisRunRead.model_validate(r) for r in run_rows],
            )
        # Memory backend
        edges = sorted(
            [e for e in self.store.lineage_edges.values() if e.project_id == project_id],
            key=lambda e: e.created_at,
        )
        artifacts = sorted(
            [a for a in self.store.artifacts.values() if a.project_id == project_id],
            key=lambda a: a.created_at,
        )
        assertions = sorted(
            [a for a in self.store.assertions.values() if a.project_id == project_id],
            key=lambda a: a.created_at,
        )
        analysis_runs = sorted(
            [r for r in self.store.analysis_runs.values() if r.project_id == project_id],
            key=lambda r: r.created_at,
        )
        return edges, artifacts, assertions, analysis_runs


# ======================================================================
# Row ↔ model helpers
# ======================================================================

def _artifact_to_row(a: ArtifactRead) -> dict[str, Any]:
    return {
        "id": a.id,
        "tenant_id": a.tenant_id,
        "project_id": a.project_id,
        "run_id": a.run_id,
        "artifact_type": a.artifact_type.value,
        "output_slot": a.output_slot,
        "storage_uri": a.storage_uri,
        "mime_type": a.mime_type,
        "sha256": a.sha256,
        "size_bytes": a.size_bytes,
        "metadata_json": json.dumps(a.metadata_json, default=str),
        "superseded_by": a.superseded_by,
        "created_at": a.created_at,
    }


def _row_to_artifact(row: dict[str, Any]) -> ArtifactRead:
    data = dict(row)
    # metadata_json may come back as dict (jsonb auto-deserialised) or str
    if isinstance(data.get("metadata_json"), str):
        data["metadata_json"] = json.loads(data["metadata_json"])
    return ArtifactRead.model_validate(data)


def _edge_to_row(e: LineageEdgeRead) -> dict[str, Any]:
    return {
        "id": e.id,
        "tenant_id": e.tenant_id,
        "project_id": e.project_id,
        "from_kind": e.from_kind.value,
        "from_id": e.from_id,
        "edge_type": e.edge_type.value,
        "to_kind": e.to_kind.value,
        "to_id": e.to_id,
        "created_at": e.created_at,
    }


def _row_to_edge(row: dict[str, Any]) -> LineageEdgeRead:
    return LineageEdgeRead.model_validate(row)
