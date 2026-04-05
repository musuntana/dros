from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_artifact_service
from ..schemas.api import (
    ArtifactDetailResponse,
    ArtifactListResponse,
    CreateArtifactRequest,
    CreateArtifactResponse,
    CreateLineageEdgeRequest,
    CreateLineageEdgeResponse,
    LineageQueryResponse,
)
from ..services.artifact_service import ArtifactService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["artifacts"])


@router.post("/artifacts", response_model=CreateArtifactResponse, status_code=status.HTTP_201_CREATED)
def create_artifact(
    project_id: UUID,
    payload: CreateArtifactRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> CreateArtifactResponse:
    return service.create_artifact(project_id, payload)


@router.get("/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactListResponse:
    return service.list_artifacts(project_id, limit=limit, offset=offset)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDetailResponse)
def get_artifact(
    project_id: UUID,
    artifact_id: UUID,
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactDetailResponse:
    return service.get_artifact(project_id, artifact_id)


@router.post("/lineage-edges", response_model=CreateLineageEdgeResponse, status_code=status.HTTP_201_CREATED)
def create_lineage_edge(
    project_id: UUID,
    payload: CreateLineageEdgeRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> CreateLineageEdgeResponse:
    return service.create_lineage_edge(project_id, payload)


@router.get("/lineage", response_model=LineageQueryResponse)
def get_lineage(
    project_id: UUID,
    service: ArtifactService = Depends(get_artifact_service),
) -> LineageQueryResponse:
    return service.get_lineage(project_id)
