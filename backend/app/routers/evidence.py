from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_evidence_service, get_review_service
from ..schemas.api import (
    CreateEvidenceChunkRequest,
    CreateEvidenceChunkResponse,
    CreateEvidenceLinkRequest,
    CreateEvidenceLinkResponse,
    EvidenceChunkDetailResponse,
    EvidenceChunkListResponse,
    EvidenceLinkDetailResponse,
    EvidenceLinkListResponse,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    EvidenceSourceListResponse,
    ResolveEvidenceRequest,
    ResolveEvidenceResponse,
    UpsertEvidenceSourceRequest,
    UpsertEvidenceSourceResponse,
    VerifyEvidenceLinkResponse,
)
from ..services.evidence_service import EvidenceService
from ..services.review_service import ReviewService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["evidence"])


@router.post("/evidence/search", response_model=EvidenceSearchResponse, status_code=status.HTTP_202_ACCEPTED)
def search_evidence(
    project_id: UUID,
    payload: EvidenceSearchRequest,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceSearchResponse:
    return service.search(project_id, payload)


@router.post("/evidence/resolve", response_model=ResolveEvidenceResponse)
def resolve_evidence(
    project_id: UUID,
    payload: ResolveEvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
) -> ResolveEvidenceResponse:
    return service.resolve(project_id, payload)


@router.post("/evidence", response_model=UpsertEvidenceSourceResponse, status_code=status.HTTP_201_CREATED)
def upsert_evidence_source(
    project_id: UUID,
    payload: UpsertEvidenceSourceRequest,
    service: EvidenceService = Depends(get_evidence_service),
) -> UpsertEvidenceSourceResponse:
    return service.upsert_source(project_id, payload)


@router.get("/evidence", response_model=EvidenceSourceListResponse)
def list_evidence_sources(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceSourceListResponse:
    return service.list_sources(project_id, limit=limit, offset=offset)


@router.post(
    "/evidence/{evidence_source_id}/chunks",
    response_model=CreateEvidenceChunkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence_chunk(
    project_id: UUID,
    evidence_source_id: UUID,
    payload: CreateEvidenceChunkRequest,
    service: EvidenceService = Depends(get_evidence_service),
) -> CreateEvidenceChunkResponse:
    return service.create_source_chunk(project_id, evidence_source_id, payload)


@router.get("/evidence/{evidence_source_id}/chunks", response_model=EvidenceChunkListResponse)
def list_evidence_chunks(
    project_id: UUID,
    evidence_source_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceChunkListResponse:
    return service.list_source_chunks(project_id, evidence_source_id, limit=limit, offset=offset)


@router.get("/evidence/chunks/{chunk_id}", response_model=EvidenceChunkDetailResponse)
def get_evidence_chunk(
    project_id: UUID,
    chunk_id: UUID,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceChunkDetailResponse:
    return service.get_source_chunk(project_id, chunk_id)


@router.post("/evidence-links", response_model=CreateEvidenceLinkResponse, status_code=status.HTTP_201_CREATED)
def create_evidence_link(
    project_id: UUID,
    payload: CreateEvidenceLinkRequest,
    service: EvidenceService = Depends(get_evidence_service),
) -> CreateEvidenceLinkResponse:
    return service.create_evidence_link(project_id, payload)


@router.get("/evidence-links", response_model=EvidenceLinkListResponse)
def list_evidence_links(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceLinkListResponse:
    return service.list_evidence_links(project_id, limit=limit, offset=offset)


@router.get("/evidence-links/{link_id}", response_model=EvidenceLinkDetailResponse)
def get_evidence_link(
    project_id: UUID,
    link_id: UUID,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceLinkDetailResponse:
    return service.get_evidence_link(project_id, link_id)


@router.post("/evidence-links/{link_id}/verify", response_model=VerifyEvidenceLinkResponse)
def verify_evidence_link(
    project_id: UUID,
    link_id: UUID,
    service: ReviewService = Depends(get_review_service),
) -> VerifyEvidenceLinkResponse:
    return service.verify_evidence_link(project_id, link_id)
