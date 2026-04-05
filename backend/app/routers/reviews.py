from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ..dependencies import get_review_service
from ..schemas.api import (
    CreateReviewRequest,
    CreateReviewResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewListResponse,
    RunVerificationRequest,
    RunVerificationResponse,
)
from ..services.review_service import ReviewService

router = APIRouter(prefix="/v1/projects/{project_id}", tags=["reviews"])


@router.post("/reviews", response_model=CreateReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    project_id: UUID,
    payload: CreateReviewRequest,
    service: ReviewService = Depends(get_review_service),
) -> CreateReviewResponse:
    return service.create_review(project_id, payload)


@router.get("/reviews", response_model=ReviewListResponse)
def list_reviews(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    return service.list_reviews(project_id, limit=limit, offset=offset)


@router.post("/reviews/{review_id}/decisions", response_model=ReviewDecisionResponse)
def decide_review(
    project_id: UUID,
    review_id: UUID,
    payload: ReviewDecisionRequest,
    service: ReviewService = Depends(get_review_service),
) -> ReviewDecisionResponse:
    return service.decide_review(project_id, review_id, payload)


@router.post("/verify", response_model=RunVerificationResponse, status_code=status.HTTP_202_ACCEPTED)
def run_verification(
    project_id: UUID,
    payload: RunVerificationRequest,
    service: ReviewService = Depends(get_review_service),
) -> RunVerificationResponse:
    return service.run_verification(project_id, payload)
