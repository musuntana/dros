from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import ComplianceLevel

T = TypeVar("T")


class DRBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TimestampedModel(DRBaseModel):
    created_at: datetime
    updated_at: datetime | None = None


class PolicyContext(DRBaseModel):
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    allow_external_llm: bool = False
    phi_cleared: bool = False


class PageInfo(DRBaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)


class Page(DRBaseModel, Generic[T]):
    items: list[T]
    page: PageInfo


class AuditMetadata(DRBaseModel):
    trace_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ObjectRef(DRBaseModel):
    object_type: str
    object_id: str


class ArtifactRef(DRBaseModel):
    artifact_id: UUID | None = None
    storage_uri: str
    sha256_digest: str | None = None

