from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_export_service
from ..schemas.api import (
    CreateExportJobRequest,
    CreateExportJobResponse,
    ExportJobDetailResponse,
    ExportJobListResponse,
)
from ..services.export_service import ExportService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["exports"])


@router.post("/exports", response_model=CreateExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_export_job(
    project_id: UUID,
    payload: CreateExportJobRequest,
    service: ExportService = Depends(get_export_service),
) -> CreateExportJobResponse:
    return service.create_export_job(project_id, payload)


@router.get("/exports", response_model=ExportJobListResponse)
def list_export_jobs(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ExportService = Depends(get_export_service),
) -> ExportJobListResponse:
    return service.list_export_jobs(project_id, limit=limit, offset=offset)


@router.get("/exports/{export_job_id}", response_model=ExportJobDetailResponse)
def get_export_job(
    project_id: UUID,
    export_job_id: UUID,
    service: ExportService = Depends(get_export_service),
) -> ExportJobDetailResponse:
    return service.get_export_job(project_id, export_job_id)
