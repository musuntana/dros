from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_workflow_service
from ..schemas.api import (
    AdvanceWorkflowRequest,
    AnalysisRunDetailResponse,
    AnalysisRunListResponse,
    CancelWorkflowRequest,
    CreateAnalysisPlanRequest,
    CreateAnalysisPlanResponse,
    CreateAnalysisRunRequest,
    CreateAnalysisRunResponse,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    WorkflowDetailResponse,
    WorkflowListResponse,
)
from ..services.workflow_service import WorkflowService

router = APIRouter(tags=["workflows"])


@router.post("/v1/projects/{project_id}/analysis/plans", response_model=CreateAnalysisPlanResponse, status_code=status.HTTP_202_ACCEPTED)
def create_analysis_plan(
    project_id: UUID,
    payload: CreateAnalysisPlanRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> CreateAnalysisPlanResponse:
    return service.create_analysis_plan(project_id, payload)


@router.post("/v1/projects/{project_id}/workflows", response_model=CreateWorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    project_id: UUID,
    payload: CreateWorkflowRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> CreateWorkflowResponse:
    return service.create_workflow(project_id, payload)


@router.get("/v1/projects/{project_id}/workflows", response_model=WorkflowListResponse)
def list_workflows(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowListResponse:
    return service.list_workflows(project_id, limit=limit, offset=offset)


@router.get("/v1/projects/{project_id}/workflows/{workflow_instance_id}", response_model=WorkflowDetailResponse)
def get_workflow(
    project_id: UUID,
    workflow_instance_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetailResponse:
    return service.get_workflow(project_id, workflow_instance_id)


@router.post("/v1/projects/{project_id}/workflows/{workflow_instance_id}/advance", response_model=WorkflowDetailResponse)
def advance_workflow(
    project_id: UUID,
    workflow_instance_id: UUID,
    payload: AdvanceWorkflowRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetailResponse:
    return service.advance_workflow(project_id, workflow_instance_id, payload)


@router.post("/v1/projects/{project_id}/workflows/{workflow_instance_id}/cancel", response_model=WorkflowDetailResponse)
def cancel_workflow(
    project_id: UUID,
    workflow_instance_id: UUID,
    payload: CancelWorkflowRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetailResponse:
    return service.cancel_workflow(project_id, workflow_instance_id, payload)


@router.post("/v1/projects/{project_id}/analysis-runs", response_model=CreateAnalysisRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_analysis_run(
    project_id: UUID,
    payload: CreateAnalysisRunRequest,
    service: WorkflowService = Depends(get_workflow_service),
) -> CreateAnalysisRunResponse:
    return service.create_analysis_run(project_id, payload)


@router.get("/v1/projects/{project_id}/analysis-runs", response_model=AnalysisRunListResponse)
def list_analysis_runs(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: WorkflowService = Depends(get_workflow_service),
) -> AnalysisRunListResponse:
    return service.list_analysis_runs(project_id, limit=limit, offset=offset)


@router.get("/v1/projects/{project_id}/analysis-runs/{run_id}", response_model=AnalysisRunDetailResponse)
def get_analysis_run(
    project_id: UUID,
    run_id: UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> AnalysisRunDetailResponse:
    return service.get_analysis_run(project_id, run_id)
