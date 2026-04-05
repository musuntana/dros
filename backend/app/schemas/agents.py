"""DR-OS Agent I/O schemas aligned to AGENTS.md.

All 4 agents: Search, Analysis, Writing, Verifier.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .common import DRBaseModel, PolicyContext
from .enums import (
    AgentExecutionStatus,
    AgentName,
    AssertionType,
    EvidenceSourceType,
    LicenseClass,
    SectionKey,
    VerificationCheckStatus,
    VerifierVerdict,
)


# ===========================================================================
# Base protocol (AGENTS.md §6)
# ===========================================================================

class AgentRequestBase(DRBaseModel):
    project_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    input_refs: list[str] = Field(default_factory=list)
    policy_context: PolicyContext = Field(default_factory=PolicyContext)


class AgentResponseBase(DRBaseModel):
    project_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    agent_name: AgentName
    status: AgentExecutionStatus
    confidence: float = Field(ge=0.0, le=1.0)
    artifacts_produced: list[str] = Field(default_factory=list)
    assertions_produced: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    needs_human_items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_terminal_lists(self) -> "AgentResponseBase":
        if self.status == AgentExecutionStatus.BLOCKED and not self.blocking_reasons:
            raise ValueError("blocked responses must include blocking_reasons")
        if self.status == AgentExecutionStatus.NEEDS_HUMAN and not self.needs_human_items:
            raise ValueError("needs_human responses must include needs_human_items")
        return self


# ===========================================================================
# Search Agent (AGENTS.md §7)
# ===========================================================================

class SearchFilters(DRBaseModel):
    source_types: list[EvidenceSourceType] = Field(default_factory=list)
    publication_year_from: int | None = Field(default=None, ge=1900, le=2200)
    publication_year_to: int | None = Field(default=None, ge=1900, le=2200)
    journals: list[str] = Field(default_factory=list)
    max_results: int = Field(default=20, ge=1, le=200)
    include_abstract: bool = True


class SearchAgentRequest(AgentRequestBase):
    task_type: Literal["literature_search"] = "literature_search"
    query: str = Field(min_length=3)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    existing_dedupe_keys: list[str] = Field(default_factory=list)


class SearchResultItem(DRBaseModel):
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    title: str = Field(min_length=1)
    journal: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    abstract: str | None = None
    license_class: LicenseClass = LicenseClass.UNKNOWN
    oa_subset_flag: bool = False
    match_reason: str = Field(min_length=1)
    dedupe_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identifier(self) -> "SearchResultItem":
        if not any([self.pmid, self.pmcid, self.doi]):
            raise ValueError("search result must include pmid, pmcid, or doi")
        return self


class SearchAgentResult(DRBaseModel):
    query: str
    normalized_query: str | None = None
    search_strategy: str = "entrez_structured"
    rerank_applied: bool = False
    search_results: list[SearchResultItem] = Field(default_factory=list)


class SearchAgentResponse(AgentResponseBase):
    agent_name: Literal[AgentName.SEARCH] = AgentName.SEARCH
    result: SearchAgentResult


# ===========================================================================
# Analysis Agent (AGENTS.md §8)
# ===========================================================================

class DatasetField(DRBaseModel):
    dataset_id: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    semantic_role: str | None = None
    nullable: bool = True


class AnalysisAgentRequest(AgentRequestBase):
    task_type: Literal["analysis_planning"] = "analysis_planning"
    study_goal: str = Field(min_length=10)
    dataset_ids: list[str] = Field(min_length=1)
    field_catalog: list[DatasetField] = Field(default_factory=list)
    candidate_templates: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class AnalysisAgentResult(DRBaseModel):
    template_id: str = Field(min_length=1)
    template_version: str = Field(min_length=1)
    parameter_json: dict[str, Any] = Field(default_factory=dict)
    preflight_checks: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class AnalysisAgentResponse(AgentResponseBase):
    agent_name: Literal[AgentName.ANALYSIS] = AgentName.ANALYSIS
    result: AnalysisAgentResult


# ===========================================================================
# Writing Agent (AGENTS.md §9)
# ===========================================================================

class VerifiedAssertionPayload(DRBaseModel):
    assertion_id: str = Field(min_length=1)
    assertion_type: AssertionType
    text_norm: str = Field(min_length=1)
    numeric_payload_json: dict[str, Any] = Field(default_factory=dict)
    source_artifact_id: str | None = None
    evidence_source_ids: list[str] = Field(default_factory=list)
    verification_status: Literal["verified"] = "verified"


class GeneratedBlock(DRBaseModel):
    block_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    assertion_ids: list[str] = Field(min_length=1)


class GeneratedAssertion(DRBaseModel):
    assertion_id: str = Field(min_length=1)
    assertion_type: AssertionType
    text_norm: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)


class WritingAgentRequest(AgentRequestBase):
    task_type: Literal["manuscript_generation"] = "manuscript_generation"
    section_key: SectionKey
    style_constraints: list[str] = Field(default_factory=list)
    verified_assertions: list[VerifiedAssertionPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_inputs(self) -> "WritingAgentRequest":
        if not self.verified_assertions:
            raise ValueError("writing agent requires verified_assertions")
        return self


class WritingAgentResult(DRBaseModel):
    section_key: SectionKey
    blocks: list[GeneratedBlock] = Field(min_length=1)
    assertions: list[GeneratedAssertion] = Field(default_factory=list)


class WritingAgentResponse(AgentResponseBase):
    agent_name: Literal[AgentName.WRITING] = AgentName.WRITING
    result: WritingAgentResult


# ===========================================================================
# Verifier Agent (AGENTS.md §10.5)
# ===========================================================================

class VerificationTarget(DRBaseModel):
    object_type: str = Field(min_length=1)
    object_id: str = Field(min_length=1)


class DraftManuscriptBlock(DRBaseModel):
    block_id: str = Field(min_length=1)
    section_key: SectionKey
    text: str = Field(min_length=1)
    assertion_ids: list[str] = Field(default_factory=list)


class ArtifactDescriptor(DRBaseModel):
    object_id: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    storage_uri: str | None = None
    metrics_json: dict[str, Any] = Field(default_factory=dict)


class VerifierAgentRequest(AgentRequestBase):
    task_type: Literal["verification"] = "verification"
    targets: list[VerificationTarget] = Field(min_length=1)
    manuscript_blocks: list[DraftManuscriptBlock] = Field(default_factory=list)
    artifacts: list[ArtifactDescriptor] = Field(default_factory=list)
    scope_checks: list[str] = Field(default_factory=lambda: [
        "scope_control",
        "causal_language",
        "meaning_preservation",
    ])


class VerifierCheck(DRBaseModel):
    name: str = Field(min_length=1)
    status: VerificationCheckStatus
    block_id: str | None = None
    message: str = Field(min_length=1)
    suggested_action: str | None = None


class VerifierAgentResult(DRBaseModel):
    verdict: VerifierVerdict
    semantic_checks: list[VerifierCheck] = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)


class VerifierAgentResponse(AgentResponseBase):
    agent_name: Literal[AgentName.VERIFIER] = AgentName.VERIFIER
    result: VerifierAgentResult
