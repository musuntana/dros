from __future__ import annotations

from functools import lru_cache

from .repositories.artifact_repository import ArtifactRepository
from .repositories.audit_repository import AuditRepository
from .repositories.base import BaseRepository
from .repositories.dataset_repository import DatasetRepository
from .repositories.evidence_repository import EvidenceRepository
from .repositories.export_repository import ExportRepository
from .repositories.manuscript_repository import ManuscriptRepository
from .repositories.project_repository import ProjectRepository
from .repositories.review_repository import ReviewRepository
from .repositories.template_repository import TemplateRepository
from .repositories.workflow_repository import WorkflowRepository
from .services.artifact_service import ArtifactService
from .services.audit_service import AuditService
from .services.dataset_service import DatasetService
from .services.evidence_service import EvidenceService
from .services.export_service import ExportService
from .services.gateway_service import GatewayService
from .services.manuscript_service import ManuscriptService
from .services.project_service import ProjectService
from .services.review_service import ReviewService
from .services.template_service import TemplateService
from .services.workflow_service import WorkflowService


@lru_cache
def get_project_service() -> ProjectService:
    return ProjectService(repository=ProjectRepository())


@lru_cache
def get_dataset_service() -> DatasetService:
    return DatasetService(repository=DatasetRepository())


@lru_cache
def get_workflow_service() -> WorkflowService:
    return WorkflowService(repository=WorkflowRepository())


@lru_cache
def get_template_service() -> TemplateService:
    return TemplateService(repository=TemplateRepository())


@lru_cache
def get_artifact_service() -> ArtifactService:
    return ArtifactService(repository=ArtifactRepository())


@lru_cache
def get_gateway_service() -> GatewayService:
    return GatewayService(repository=BaseRepository())


@lru_cache
def get_evidence_service() -> EvidenceService:
    return EvidenceService(repository=EvidenceRepository())


@lru_cache
def get_manuscript_service() -> ManuscriptService:
    return ManuscriptService(repository=ManuscriptRepository())


@lru_cache
def get_review_service() -> ReviewService:
    return ReviewService(repository=ReviewRepository())


@lru_cache
def get_export_service() -> ExportService:
    return ExportService(repository=ExportRepository())


@lru_cache
def get_audit_service() -> AuditService:
    return AuditService(repository=AuditRepository())
