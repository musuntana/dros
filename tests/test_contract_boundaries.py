from __future__ import annotations

from pathlib import Path

from backend.app.schemas.agents import VerifierAgentResult, VerifierCheck, WritingAgentRequest
from backend.app.schemas.api import (
    CreateAnalysisRunRequest,
    CreateArtifactRequest,
    CreateAssertionRequest,
    CreateDatasetSnapshotRequest,
    CreateEvidenceLinkRequest,
    CreateExportJobRequest,
    CreateLineageEdgeRequest,
    CreateManuscriptBlockRequest,
    CreateManuscriptRequest,
    CreateReviewRequest,
    CreateWorkflowRequest,
)
from backend.app.schemas.domain import (
    AssertionCreate,
    DatasetCreate,
    DatasetSnapshotCreate,
    EvidenceLinkCreate,
    ExportJobCreate,
    ManuscriptBlockCreate,
    ManuscriptCreate,
    ReviewCreate,
    WorkflowInstanceCreate,
)
from backend.app.schemas.enums import AssertionType, SectionKey, VerificationCheckStatus


def test_path_scoped_requests_do_not_duplicate_parent_ids() -> None:
    request_models = {
        CreateDatasetSnapshotRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateWorkflowRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateAnalysisRunRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateArtifactRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateAssertionRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateLineageEdgeRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateEvidenceLinkRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateManuscriptRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateManuscriptBlockRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateReviewRequest: {"project_id", "dataset_id", "manuscript_id"},
        CreateExportJobRequest: {"project_id", "dataset_id"},
    }
    for model, forbidden_fields in request_models.items():
        properties = model.model_json_schema()["properties"]
        for field_name in forbidden_fields:
            assert field_name not in properties


def test_domain_create_models_do_not_duplicate_path_scopes() -> None:
    model_forbidden_fields = {
        DatasetCreate: {"project_id"},
        DatasetSnapshotCreate: {"dataset_id"},
        WorkflowInstanceCreate: {"project_id"},
        AssertionCreate: {"project_id"},
        EvidenceLinkCreate: {"project_id"},
        ManuscriptCreate: {"project_id"},
        ManuscriptBlockCreate: {"manuscript_id"},
        ReviewCreate: {"project_id"},
        ExportJobCreate: {"project_id"},
    }
    for model, forbidden_fields in model_forbidden_fields.items():
        properties = model.model_json_schema()["properties"]
        for field_name in forbidden_fields:
            assert field_name not in properties


def test_agent_contracts_consume_verified_assertions_and_semantic_checks() -> None:
    writing_schema = WritingAgentRequest.model_json_schema()["properties"]
    assert "verified_assertions" in writing_schema
    assert "analysis_payloads" not in writing_schema
    assert "evidence_payloads" not in writing_schema

    verifier_result = VerifierAgentResult(
        verdict="warning",
        semantic_checks=[
            VerifierCheck(
                name="ScopeControl",
                status=VerificationCheckStatus.WARNING,
                block_id="blk_1",
                message="causal wording exceeds the evidence",
                suggested_action="replace_with_associated_with",
            )
        ],
        recommended_actions=["replace causal wording"],
    )
    assert verifier_result.verdict.value == "warning"

    request = WritingAgentRequest(
        project_id="proj_1",
        task_id="task_1",
        trace_id="trace_1",
        actor_id="actor_1",
        section_key=SectionKey.RESULTS,
        verified_assertions=[
            {
                "assertion_id": "ast_1",
                "assertion_type": AssertionType.RESULT,
                "text_norm": "marker associated with survival",
                "source_artifact_id": "artifact_1",
            }
        ],
    )
    assert request.verified_assertions[0].verification_status == "verified"


def test_no_public_service_stub_methods_remain() -> None:
    service_dir = Path(__file__).resolve().parents[1] / "backend" / "app" / "services"
    offenders = [
        path.name
        for path in service_dir.glob("*.py")
        if path.name != "base.py" and "self.not_implemented(" in path.read_text()
    ]
    assert offenders == []
