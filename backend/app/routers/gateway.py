from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from ..dependencies import get_gateway_service
from ..schemas.api import (
    SessionRead,
    SignedArtifactUrlResponse,
    SignedUploadRequest,
    SignedUploadResponse,
    UploadCompleteRequest,
    UploadCompleteResponse,
)
from ..services.gateway_service import GatewayService

router = APIRouter(prefix="/v1", tags=["gateway"])


@router.get("/session", response_model=SessionRead)
def get_session(service: GatewayService = Depends(get_gateway_service)) -> SessionRead:
    return service.get_session()


@router.post("/uploads/sign", response_model=SignedUploadResponse)
def sign_upload(
    payload: SignedUploadRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> SignedUploadResponse:
    return service.sign_upload(payload)


@router.post("/uploads/complete", response_model=UploadCompleteResponse)
def complete_upload(
    payload: UploadCompleteRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> UploadCompleteResponse:
    return service.complete_upload(payload)


@router.get("/projects/{project_id}/events")
async def stream_project_events(
    project_id: UUID,
    request: Request,
    once: bool = Query(default=False),
    service: GatewayService = Depends(get_gateway_service),
) -> StreamingResponse:
    service.authorize_project_events(project_id)
    return StreamingResponse(
        service.stream_project_events(project_id, request, once=once),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/projects/{project_id}/artifacts/{artifact_id}/download-url", response_model=SignedArtifactUrlResponse)
def get_artifact_download_url(
    project_id: UUID,
    artifact_id: UUID,
    service: GatewayService = Depends(get_gateway_service),
) -> SignedArtifactUrlResponse:
    return service.get_artifact_download_url(project_id, artifact_id)
