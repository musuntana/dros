from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_dataset_service, get_review_service
from ..schemas.api import (
    CreateDatasetResponse,
    CreateDatasetSnapshotRequest,
    CreateDatasetSnapshotResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetPolicyCheckResponse,
    DatasetSnapshotListResponse,
    ImportPublicDatasetRequest,
    RegisterUploadDatasetRequest,
)
from ..services.dataset_service import DatasetService
from ..services.review_service import ReviewService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["datasets"])


@router.post("/datasets/import-public", response_model=CreateDatasetResponse, status_code=status.HTTP_201_CREATED)
def import_public_dataset(
    project_id: UUID,
    payload: ImportPublicDatasetRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> CreateDatasetResponse:
    return service.import_public_dataset(project_id, payload)


@router.post("/datasets/register-upload", response_model=CreateDatasetResponse, status_code=status.HTTP_201_CREATED)
def register_upload_dataset(
    project_id: UUID,
    payload: RegisterUploadDatasetRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> CreateDatasetResponse:
    return service.register_upload_dataset(project_id, payload)


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetListResponse:
    return service.list_datasets(project_id, limit=limit, offset=offset)


@router.get("/datasets/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    project_id: UUID,
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetDetailResponse:
    return service.get_dataset(project_id, dataset_id)


@router.post("/datasets/{dataset_id}/snapshots", response_model=CreateDatasetSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    project_id: UUID,
    dataset_id: UUID,
    payload: CreateDatasetSnapshotRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> CreateDatasetSnapshotResponse:
    return service.create_snapshot(project_id, dataset_id, payload)


@router.get("/datasets/{dataset_id}/snapshots", response_model=DatasetSnapshotListResponse)
def list_snapshots(
    project_id: UUID,
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetSnapshotListResponse:
    return service.list_snapshots(project_id, dataset_id)


@router.post("/datasets/{dataset_id}/policy-checks", response_model=DatasetPolicyCheckResponse)
def run_policy_checks(
    project_id: UUID,
    dataset_id: UUID,
    service: ReviewService = Depends(get_review_service),
) -> DatasetPolicyCheckResponse:
    return service.run_dataset_policy_checks(project_id, dataset_id)
