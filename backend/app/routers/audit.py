from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_audit_service
from ..schemas.api import AuditEventDetailResponse, AuditEventListResponse, AuditReplayResponse
from ..services.audit_service import AuditService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["audit"])


@router.get("/audit-events", response_model=AuditEventListResponse)
def list_audit_events(
    project_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: AuditService = Depends(get_audit_service),
) -> AuditEventListResponse:
    return service.list_events(project_id, limit=limit, offset=offset)


@router.get("/audit-events/{event_id}", response_model=AuditEventDetailResponse)
def get_audit_event(
    project_id: UUID,
    event_id: UUID,
    service: AuditService = Depends(get_audit_service),
) -> AuditEventDetailResponse:
    return service.get_event(project_id, event_id)


internal_router = APIRouter(prefix="/v1/internal/audit", tags=["audit"])


@internal_router.post("/replay", response_model=AuditReplayResponse, status_code=status.HTTP_202_ACCEPTED)
def replay_audit_chain(
    service: AuditService = Depends(get_audit_service),
) -> AuditReplayResponse:
    return service.replay()
