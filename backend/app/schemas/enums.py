"""DR-OS unified enum definitions.

DDL-aligned enums match PostgreSQL types in sql/ddl_research_ledger_v2.sql.
Application enums serve agents, gates, and internal protocols.
"""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


# ===========================================================================
# DDL-aligned: Tenant & Access
# ===========================================================================

class TenantTier(StrEnum):
    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class DeploymentMode(StrEnum):
    SAAS = "saas"
    PRIVATE_VPC = "private_vpc"
    ON_PREM = "on_prem"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class PrincipalSubjectType(StrEnum):
    USER = "user"
    SERVICE = "service"


class PrincipalStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    INVITED = "invited"


class ProjectType(StrEnum):
    PUBLIC_OMICS = "public_omics"
    CLINICAL_RETROSPECTIVE = "clinical_retrospective"
    CASE_REPORT = "case_report"
    GRANT = "grant"


class ProjectState(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ComplianceLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CLINICAL = "clinical"


class ProjectRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


# ===========================================================================
# DDL-aligned: Data & Execution
# ===========================================================================

class DatasetSourceKind(StrEnum):
    UPLOAD = "upload"
    GEO = "geo"
    TCGA = "tcga"
    SEER = "seer"
    MANUAL = "manual"


class PiiLevel(StrEnum):
    NONE = "none"
    LIMITED = "limited"
    DIRECT = "direct"


class LicenseClass(StrEnum):
    UNKNOWN = "unknown"
    PUBLIC = "public"
    METADATA_ONLY = "metadata_only"
    PMC_OA_SUBSET = "pmc_oa_subset"
    RESTRICTED = "restricted"
    INTERNAL = "internal"


class DeidStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PhiScanStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"


class TemplateReviewStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class WorkflowState(StrEnum):
    CREATED = "created"
    RETRIEVING = "retrieving"
    RETRIEVED = "retrieved"
    STRUCTURING = "structuring"
    STRUCTURED = "structured"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    ASSERTING = "asserting"
    ASSERTED = "asserted"
    WRITING = "writing"
    VERIFYING = "verifying"
    APPROVED = "approved"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    EXPORTED = "exported"
    FAILED = "failed"


class WorkflowBackend(StrEnum):
    QUEUE_WORKERS = "queue_workers"
    TEMPORAL = "temporal"


class TaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    FAILED = "failed"
    CANCELED = "canceled"


class AnalysisRunState(StrEnum):
    CREATED = "created"
    REQUESTED = "requested"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELED = "canceled"


class ArtifactType(StrEnum):
    DATASET_SNAPSHOT = "dataset_snapshot"
    RESULT_JSON = "result_json"
    TABLE = "table"
    FIGURE = "figure"
    LOG = "log"
    MANIFEST = "manifest"
    DOCX = "docx"
    PDF = "pdf"
    ZIP = "zip"
    EVIDENCE_ATTACHMENT = "evidence_attachment"


class LineageKind(StrEnum):
    TENANT = "tenant"
    PRINCIPAL = "principal"
    PROJECT = "project"
    DATASET = "dataset"
    DATASET_SNAPSHOT = "dataset_snapshot"
    WORKFLOW_INSTANCE = "workflow_instance"
    WORKFLOW_TASK = "workflow_task"
    ANALYSIS_TEMPLATE = "analysis_template"
    ANALYSIS_RUN = "analysis_run"
    ARTIFACT = "artifact"
    ASSERTION = "assertion"
    EVIDENCE_SOURCE = "evidence_source"
    EVIDENCE_CHUNK = "evidence_chunk"
    MANUSCRIPT = "manuscript"
    MANUSCRIPT_BLOCK = "manuscript_block"
    REVIEW = "review"
    EXPORT_JOB = "export_job"


class LineageEdgeType(StrEnum):
    INPUT_OF = "input_of"
    EMITS = "emits"
    DERIVES = "derives"
    SUPERSEDES = "supersedes"
    GROUNDS = "grounds"
    CITED_BY = "cited_by"
    ATTACHED_TO = "attached_to"
    REVIEWED_BY = "reviewed_by"
    EXPORTS = "exports"


# ===========================================================================
# DDL-aligned: Evidence & Writing
# ===========================================================================

class EvidenceSourceType(StrEnum):
    PUBMED = "pubmed"
    PMC = "pmc"
    GEO = "geo"
    TCGA = "tcga"
    MANUAL = "manual"


class AssertionType(StrEnum):
    BACKGROUND = "background"
    METHOD = "method"
    RESULT = "result"
    LIMITATION = "limitation"


class AssertionState(StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    STALE = "stale"


class EvidenceRelationType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    METHOD_REF = "method_ref"
    BACKGROUND_REF = "background_ref"


class VerifierStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"


class ManuscriptType(StrEnum):
    MANUSCRIPT = "manuscript"
    ABSTRACT = "abstract"
    GRANT_RESPONSE = "grant_response"


class ManuscriptState(StrEnum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    EXPORTED = "exported"
    ARCHIVED = "archived"


class BlockType(StrEnum):
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    CITATION_LIST = "citation_list"


class BlockState(StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"


# ===========================================================================
# DDL-aligned: Governance
# ===========================================================================

class ReviewType(StrEnum):
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"
    MANUSCRIPT = "manuscript"
    EXPORT = "export"


class ReviewState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ExportFormat(StrEnum):
    DOCX = "docx"
    PDF = "pdf"
    ZIP = "zip"


class ExportState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ActorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


# ===========================================================================
# Application-level: Section keys
# DDL uses TEXT for section_key; enum provides validation in agent I/O
# ===========================================================================

class SectionKey(StrEnum):
    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    FIGURE_LEGEND = "figure_legend"
    TABLE_NOTE = "table_note"
    APPENDIX = "appendix"


# ===========================================================================
# Application-level: Agents
# ===========================================================================

class AgentName(StrEnum):
    SEARCH = "search_agent"
    ANALYSIS = "analysis_agent"
    WRITING = "writing_agent"
    VERIFIER = "verifier_agent"
    WORKFLOW = "workflow_service"
    EVIDENCE_STRUCTURING = "evidence_structuring_service"


class AgentExecutionStatus(StrEnum):
    OK = "ok"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    FAILED = "failed"


# ===========================================================================
# Application-level: Gates
# ===========================================================================

class GateName(StrEnum):
    CITATION_RESOLVER = "citation_resolver"
    CLAIM_EVIDENCE_BINDER = "claim_evidence_binder"
    DATA_CONSISTENCY_CHECKER = "data_consistency_checker"
    LICENSE_GUARD = "license_guard"
    SOURCE_INTEGRITY = "source_integrity"
    DATA_FINGERPRINT = "data_fingerprint"
    TEMPLATE_WHITELIST = "template_whitelist"
    STAT_CONSISTENCY = "stat_consistency"
    PHI = "phi"
    EXPORT_APPROVAL = "export_approval"


class GateStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"


# ===========================================================================
# Application-level: Verifier Agent
# ===========================================================================

class VerificationCheckStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    NEEDS_HUMAN = "needs_human"


class VerifierVerdict(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    NEEDS_HUMAN = "needs_human"
