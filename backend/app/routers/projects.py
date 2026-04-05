from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_project_service
from ..schemas.api import (
    AddProjectMemberRequest,
    AddProjectMemberResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectMemberListResponse,
    UpdateProjectRequest,
)
from ..services.project_service import ProjectService

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service),
) -> CreateProjectResponse:
    return service.create_project(payload)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    return service.list_projects(limit=limit, offset=offset)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectDetailResponse:
    return service.get_project(project_id)


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
def update_project(
    project_id: UUID,
    payload: UpdateProjectRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectDetailResponse:
    return service.update_project(project_id, payload)


@router.post("/{project_id}/members", response_model=AddProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: UUID,
    payload: AddProjectMemberRequest,
    service: ProjectService = Depends(get_project_service),
) -> AddProjectMemberResponse:
    return service.add_member(project_id, payload)


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
def list_members(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectMemberListResponse:
    return service.list_members(project_id)
