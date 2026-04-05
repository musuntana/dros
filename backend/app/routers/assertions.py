from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_manuscript_service
from ..schemas.api import (
    AssertionDetailResponse,
    AssertionListResponse,
    CreateAssertionRequest,
    CreateAssertionResponse,
)
from ..services.manuscript_service import ManuscriptService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["assertions"])


@router.post("/assertions", response_model=CreateAssertionResponse, status_code=status.HTTP_201_CREATED)
def create_assertion(
    project_id: UUID,
    payload: CreateAssertionRequest,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> CreateAssertionResponse:
    return service.create_assertion(project_id, payload)


@router.get("/assertions", response_model=AssertionListResponse)
def list_assertions(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ManuscriptService = Depends(get_manuscript_service),
) -> AssertionListResponse:
    return service.list_assertions(project_id, limit=limit, offset=offset)


@router.get("/assertions/{assertion_id}", response_model=AssertionDetailResponse)
def get_assertion(
    project_id: UUID,
    assertion_id: UUID,
    service: ManuscriptService = Depends(get_manuscript_service),
) -> AssertionDetailResponse:
    return service.get_assertion(project_id, assertion_id)
