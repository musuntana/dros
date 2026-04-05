from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from ..schemas.api import TemplateDetailResponse, TemplateListResponse
from .base import BaseService


@dataclass(slots=True)
class TemplateService(BaseService):
    repository: object

    def list_templates(self) -> TemplateListResponse:
        self.require_scopes("workflows:read")
        items = list(self.repository.store.analysis_templates.values())
        items.sort(key=lambda template: (template.code, template.version))
        return TemplateListResponse(items=items)

    def get_template(self, template_id: str) -> TemplateDetailResponse:
        self.require_scopes("workflows:read")
        for template in self.repository.store.analysis_templates.values():
            if str(template.id) == template_id or template.code == template_id:
                return TemplateDetailResponse(template=template)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"template {template_id} not found")
