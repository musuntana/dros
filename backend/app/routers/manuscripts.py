from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ..dependencies import get_manuscript_service
from ..schemas.api import (
    CreateManuscriptBlockRequest,
    CreateManuscriptBlockResponse,
    CreateManuscriptRequest,
    CreateManuscriptResponse,
    CreateManuscriptVersionRequest,
    CreateManuscriptVersionResponse,
    ManuscriptBlockListResponse,
    ManuscriptDetailResponse,
    ManuscriptListResponse,
    RenderManuscriptResponse,
)
from ..services.manuscript_service import ManuscriptService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["manuscripts"])


@router.post("/manuscripts", response_model=CreateManuscriptResponse, status_code=status.HTTP_201_CREATED)
def create_manuscript(
    project_id: UUID,
    payload: CreateManuscriptRequest,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> CreateManuscriptResponse:
    return service.create_manuscript(project_id, payload)


@router.get("/manuscripts", response_model=ManuscriptListResponse)
def list_manuscripts(
    project_id: UUID,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> ManuscriptListResponse:
    return service.list_manuscripts(project_id)


@router.get("/manuscripts/{manuscript_id}", response_model=ManuscriptDetailResponse)
def get_manuscript(
    project_id: UUID,
    manuscript_id: UUID,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> ManuscriptDetailResponse:
    return service.get_manuscript(project_id, manuscript_id)


@router.post("/manuscripts/{manuscript_id}/blocks", response_model=CreateManuscriptBlockResponse, status_code=status.HTTP_201_CREATED)
def create_block(
    project_id: UUID,
    manuscript_id: UUID,
    payload: CreateManuscriptBlockRequest,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> CreateManuscriptBlockResponse:
    return service.create_block(project_id, manuscript_id, payload)


@router.get("/manuscripts/{manuscript_id}/blocks", response_model=ManuscriptBlockListResponse)
def list_blocks(
    project_id: UUID,
    manuscript_id: UUID,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> ManuscriptBlockListResponse:
    return service.list_blocks(project_id, manuscript_id)


@router.post("/manuscripts/{manuscript_id}/versions", response_model=CreateManuscriptVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    project_id: UUID,
    manuscript_id: UUID,
    payload: CreateManuscriptVersionRequest,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> CreateManuscriptVersionResponse:
    return service.create_version(project_id, manuscript_id, payload)


@router.post("/manuscripts/{manuscript_id}/render", response_model=RenderManuscriptResponse)
def render_manuscript(
    project_id: UUID,
    manuscript_id: UUID,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> RenderManuscriptResponse:
    return service.render(project_id, manuscript_id)
