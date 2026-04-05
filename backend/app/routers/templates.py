from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_template_service
from ..schemas.api import TemplateDetailResponse, TemplateListResponse
from ..services.template_service import TemplateService

router = APIRouter(prefix="/v1/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def list_templates(
    service: TemplateService = Depends(get_template_service),
) -> TemplateListResponse:
    return service.list_templates()


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
) -> TemplateDetailResponse:
    return service.get_template(template_id)
