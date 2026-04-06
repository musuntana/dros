from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest
import jwt
from fastapi.testclient import TestClient

from backend.app.auth import build_dev_jwt_claims
from backend.app import dependencies
from backend.app.main import create_app
from backend.app.repositories.base import reload_memory_store
from backend.app.schemas.domain import AnalysisTemplateRead
from backend.app.schemas.enums import LicenseClass
from backend.app.schemas.enums import TemplateReviewStatus
from backend.app.services.ncbi_adapter import NCBIAdapter, NCBIEvidenceRecord
from backend.app.settings import get_settings


def test_minimal_control_plane_flow() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "LUAD Survival Study",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_payload = dataset_response.json()
    dataset_id = dataset_payload["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/tcga-luad-v2.csv",
            "input_hash_sha256": "b" * 64,
            "row_count": 128,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    templates_response = client.get("/v1/templates")
    assert templates_response.status_code == 200
    template_id = templates_response.json()["items"][0]["id"]

    plan_response = client.post(
        f"/v1/projects/{project_id}/analysis/plans",
        json={
            "study_goal": "Estimate the survival association for the imported cohort",
            "dataset_ids": [dataset_id],
            "candidate_templates": ["survival.cox.v1"],
            "assumptions": [],
        },
    )
    assert plan_response.status_code == 202
    assert plan_response.json()["plan"]["template_id"] == template_id

    workflow_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["workflow"]["id"]

    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "workflow_instance_id": workflow_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 7,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    run_list_response = client.get(f"/v1/projects/{project_id}/analysis-runs")
    assert run_list_response.status_code == 200
    assert run_list_response.json()["items"]["page"]["total"] == 1
    assert run_list_response.json()["items"]["items"][0]["id"] == run_id

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "run_id": run_id,
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/run-1/result.json",
            "sha256": "c" * 64,
            "metadata_json": {"kind": "cox_summary"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "cox regression showed the marker was associated with overall survival",
            "numeric_payload_json": {"hazard_ratio": 0.65, "p_value": 0.03},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "cox_summary"},
            "claim_hash": "d" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]
    assert assertion_response.json()["assertion"]["state"] == "draft"

    verify_response = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"target_ids": [assertion_id]},
    )
    assert verify_response.status_code == 202
    assert verify_response.json()["blocking_summary"] == []
    assert verify_response.json()["gate_evaluations"][0]["status"] == "passed"

    assertion_detail = client.get(f"/v1/projects/{project_id}/assertions/{assertion_id}")
    assert assertion_detail.status_code == 200
    assert assertion_detail.json()["assertion"]["state"] == "verified"
    assert assertion_detail.json()["evidence_links"] == []

    evidence_source_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "manual",
            "external_id_norm": "PMID:12345678",
            "title": "Linked evidence source",
            "license_class": "public",
            "oa_subset_flag": False,
            "metadata_json": {
                "kind": "supporting_reference",
                "preview_text": "The linked source supports the observed survival association.",
            },
        },
    )
    assert evidence_source_response.status_code == 201
    evidence_source_id = evidence_source_response.json()["evidence_source"]["id"]

    evidence_chunk_list = client.get(f"/v1/projects/{project_id}/evidence/{evidence_source_id}/chunks")
    assert evidence_chunk_list.status_code == 200
    assert evidence_chunk_list.json()["items"]["page"]["total"] == 1
    evidence_chunk_id = evidence_chunk_list.json()["items"]["items"][0]["id"]

    evidence_chunk_detail = client.get(f"/v1/projects/{project_id}/evidence/chunks/{evidence_chunk_id}")
    assert evidence_chunk_detail.status_code == 200
    assert evidence_chunk_detail.json()["evidence_chunk"]["id"] == evidence_chunk_id
    assert evidence_chunk_detail.json()["evidence_source"]["id"] == evidence_source_id

    evidence_link_response = client.post(
        f"/v1/projects/{project_id}/evidence-links",
        json={
            "assertion_id": assertion_id,
            "evidence_source_id": evidence_source_id,
            "relation_type": "supports",
            "confidence": 0.91,
            "source_span_start": 10,
            "source_span_end": 24,
        },
    )
    assert evidence_link_response.status_code == 201
    evidence_link_id = evidence_link_response.json()["evidence_link"]["id"]

    evidence_link_detail = client.get(f"/v1/projects/{project_id}/evidence-links/{evidence_link_id}")
    assert evidence_link_detail.status_code == 200
    assert evidence_link_detail.json()["evidence_link"]["id"] == evidence_link_id
    assert evidence_link_detail.json()["assertion"]["id"] == assertion_id
    assert evidence_link_detail.json()["evidence_source"]["id"] == evidence_source_id
    assert evidence_link_detail.json()["source_chunk"]["id"] == evidence_chunk_id
    assert evidence_link_detail.json()["source_artifact"]["id"] == artifact_id

    lineage_response = client.get(f"/v1/projects/{project_id}/lineage")
    assert lineage_response.status_code == 200
    lineage = lineage_response.json()
    edge_types = {edge["edge_type"] for edge in lineage["edges"]}
    assert {"input_of", "emits", "derives"} <= edge_types
    assert {run["id"] for run in lineage["analysis_runs"]} == {run_id}

    project_detail = client.get(f"/v1/projects/{project_id}")
    assert project_detail.status_code == 200
    assert project_detail.json()["latest_snapshot"]["id"] == snapshot_id
    assert project_detail.json()["active_workflows"][0]["id"] == workflow_id


def test_gateway_routes_are_usable() -> None:
    client = TestClient(create_app())

    session_response = client.get("/v1/session")
    assert session_response.status_code == 200
    assert session_response.json()["tenant_id"] == "00000000-0000-0000-0000-000000000001"

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Gateway Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    sign_response = client.post(
        "/v1/uploads/sign",
        json={"filename": "cohort.csv", "content_type": "text/csv", "size_bytes": 18},
    )
    assert sign_response.status_code == 200
    sign_payload = sign_response.json()
    upload_path = urlparse(sign_payload["upload_url"]).path
    upload_bytes = b"gene,value\nEGFR,1\n"
    with open(upload_path, "wb") as handle:
        handle.write(upload_bytes)

    digest = sha256(upload_bytes).hexdigest()
    complete_response = client.post(
        "/v1/uploads/complete",
        json={"object_key": sign_payload["object_key"], "sha256": digest},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["file_ref"] == sign_payload["object_key"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/register-upload",
        json={"display_name": "Clinical upload", "file_ref": sign_payload["object_key"]},
    )
    assert dataset_response.status_code == 201

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "log",
            "storage_uri": f"object://{sign_payload['object_key']}",
            "mime_type": "text/csv",
            "sha256": digest,
            "size_bytes": len(upload_bytes),
            "metadata_json": {"source": "gateway-upload"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    download_response = client.get(f"/v1/projects/{project_id}/artifacts/{artifact_id}/download-url")
    assert download_response.status_code == 200
    assert download_response.json()["download_url"].startswith("file://")

    with client.stream("GET", f"/v1/projects/{project_id}/events?once=true") as event_response:
        assert event_response.status_code == 200
        assert event_response.headers["content-type"].startswith("text/event-stream")
        payload = None
        for line in event_response.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
                break
        assert payload is not None
        assert payload["project_id"] == project_id
        assert payload["event_name"] in {
            "artifact.created",
            "dataset.registered_upload",
            "project.created",
        }

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    event_types = {event["event_type"] for event in audit_response.json()["events"]["items"]}
    assert "dataset.registered_upload" in event_types
    assert "artifact.download_url.issued" in event_types


def test_evidence_chunk_create_requires_matching_source_on_link() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Evidence Chunk Validation Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/evidence-chunk/result.json",
            "sha256": "9" * 64,
            "metadata_json": {"kind": "chunk_validation"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "chunk validation assertion",
            "numeric_payload_json": {},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "chunk_validation"},
            "claim_hash": "8" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]

    source_a_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "manual",
            "external_id_norm": "PMID:20000001",
            "title": "Chunk Source A",
            "license_class": "public",
            "oa_subset_flag": False,
            "metadata_json": {},
        },
    )
    assert source_a_response.status_code == 201
    source_a_id = source_a_response.json()["evidence_source"]["id"]

    source_b_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "manual",
            "external_id_norm": "PMID:20000002",
            "title": "Chunk Source B",
            "license_class": "public",
            "oa_subset_flag": False,
            "metadata_json": {},
        },
    )
    assert source_b_response.status_code == 201
    source_b_id = source_b_response.json()["evidence_source"]["id"]

    create_chunk_response = client.post(
        f"/v1/projects/{project_id}/evidence/{source_a_id}/chunks",
        json={
            "section_label": "results",
            "text": "Chunk source A reports a validated effect size.",
            "char_start": 12,
        },
    )
    assert create_chunk_response.status_code == 201
    chunk_id = create_chunk_response.json()["evidence_chunk"]["id"]

    link_response = client.post(
        f"/v1/projects/{project_id}/evidence-links",
        json={
            "assertion_id": assertion_id,
            "evidence_source_id": source_b_id,
            "relation_type": "supports",
            "source_chunk_id": chunk_id,
            "source_span_start": 0,
            "source_span_end": 10,
        },
    )
    assert link_response.status_code == 422
    assert link_response.json()["detail"] == "source_chunk_id must belong to evidence_source_id"


def test_upload_dataset_policy_checks_emit_blocked_snapshot_event_once() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Policy Block Project",
            "project_type": "clinical_retrospective",
            "compliance_level": "clinical",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/register-upload",
        json={"display_name": "Clinical upload", "file_ref": "uploads/policy-block.csv"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]
    snapshot_id = dataset_response.json()["snapshot"]["id"]

    first_policy_check = client.post(f"/v1/projects/{project_id}/datasets/{dataset_id}/policy-checks")
    assert first_policy_check.status_code == 200
    assert first_policy_check.json() == {
        "snapshot_id": snapshot_id,
        "phi_scan_status": "pending",
        "deid_status": "pending",
        "blocking_reasons": ["phi_scan_pending", "deidentification_pending"],
        "allowed": False,
    }

    second_policy_check = client.post(f"/v1/projects/{project_id}/datasets/{dataset_id}/policy-checks")
    assert second_policy_check.status_code == 200
    assert second_policy_check.json()["blocking_reasons"] == ["phi_scan_pending", "deidentification_pending"]
    assert second_policy_check.json()["allowed"] is False

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    blocked_events = [
        event
        for event in audit_response.json()["events"]["items"]
        if event["event_type"] == "dataset.snapshot.blocked" and event["target_id"] == snapshot_id
    ]
    assert len(blocked_events) == 1
    assert blocked_events[0]["payload_json"] == {
        "dataset_id": dataset_id,
        "snapshot_id": snapshot_id,
        "blocked_checks": ["phi_scan_pending", "deidentification_pending"],
        "reason": "phi_scan_pending; deidentification_pending",
    }

    streamed_events: list[dict[str, object]] = []
    with client.stream("GET", f"/v1/projects/{project_id}/events?once=true") as event_response:
        assert event_response.status_code == 200
        for line in event_response.iter_lines():
            if line.startswith("data: "):
                streamed_events.append(json.loads(line.removeprefix("data: ")))

    blocked_event = next(
        event
        for event in streamed_events
        if event["event_name"] == "dataset.snapshot.blocked" and event["payload"]["snapshot_id"] == snapshot_id
    )
    assert blocked_event["produced_by"] == "review_service"
    assert blocked_event["payload"] == {
        "dataset_id": dataset_id,
        "snapshot_id": snapshot_id,
        "blocked_checks": ["phi_scan_pending", "deidentification_pending"],
        "reason": "phi_scan_pending; deidentification_pending",
    }


def test_request_auth_headers_scope_project_visibility_and_audit() -> None:
    client = TestClient(create_app())

    tenant_id = str(uuid4())
    owner_id = str(uuid4())
    reviewer_id = str(uuid4())
    owner_headers = {
        "X-Dros-Tenant-Id": tenant_id,
        "X-Dros-Actor-Id": owner_id,
        "X-Dros-Project-Role": "owner",
        "X-Dros-Scopes": "projects:read,projects:write,members:write,datasets:read,datasets:write,reviews:read,reviews:write,audit:read",
        "X-Request-Id": "req-auth-owner",
        "X-Trace-Id": "trace-auth-owner",
    }
    reviewer_headers = {
        "X-Dros-Tenant-Id": tenant_id,
        "X-Dros-Actor-Id": reviewer_id,
        "X-Dros-Project-Role": "reviewer",
        "X-Dros-Scopes": "projects:read,reviews:read",
    }

    session_response = client.get("/v1/session", headers=owner_headers)
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["actor_id"] == owner_id
    assert session_payload["tenant_id"] == tenant_id
    assert session_payload["principal_id"] == owner_id
    assert session_payload["scopes_json"]["project_role"] == "owner"
    assert session_payload["scopes_json"]["auth_source"] == "headers"
    assert session_payload["scopes_json"]["request_id"] == "req-auth-owner"
    assert session_payload["scopes_json"]["trace_id"] == "trace-auth-owner"
    assert "members:write" in session_payload["scopes_json"]["scope_tokens"]

    project_response = client.post(
        "/v1/projects",
        headers=owner_headers,
        json={
            "name": "Scoped Auth Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": owner_id,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    owner_list = client.get("/v1/projects", headers=owner_headers)
    assert owner_list.status_code == 200
    assert owner_list.json()["items"]["page"]["total"] == 1
    assert owner_list.json()["items"]["items"][0]["id"] == project_id

    reviewer_list = client.get("/v1/projects", headers=reviewer_headers)
    assert reviewer_list.status_code == 200
    assert reviewer_list.json()["items"]["page"]["total"] == 0

    forbidden_detail = client.get(f"/v1/projects/{project_id}", headers=reviewer_headers)
    assert forbidden_detail.status_code == 403

    add_member_response = client.post(
        f"/v1/projects/{project_id}/members",
        headers=owner_headers,
        json={"principal_id": reviewer_id, "role": "reviewer"},
    )
    assert add_member_response.status_code == 201

    reviewer_detail = client.get(f"/v1/projects/{project_id}", headers=reviewer_headers)
    assert reviewer_detail.status_code == 200
    assert reviewer_detail.json()["project"]["id"] == project_id

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        headers=owner_headers,
        json={"accession": "TCGA-SCOPED-AUTH", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    other_tenant_headers = {
        "X-Dros-Tenant-Id": str(uuid4()),
        "X-Dros-Actor-Id": owner_id,
        "X-Dros-Project-Role": "owner",
        "X-Dros-Scopes": owner_headers["X-Dros-Scopes"],
    }
    cross_tenant_dataset = client.get(
        f"/v1/projects/{project_id}/datasets/{dataset_id}",
        headers=other_tenant_headers,
    )
    assert cross_tenant_dataset.status_code == 404

    review_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        headers=owner_headers,
        json={
            "review_type": "manuscript",
            "target_kind": "project",
            "target_id": project_id,
            "reviewer_id": reviewer_id,
            "comments": "scoped review request",
        },
    )
    assert review_response.status_code == 201

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events", headers=owner_headers)
    assert audit_response.status_code == 200
    audit_items = audit_response.json()["events"]["items"]
    project_created = next(event for event in audit_items if event["event_type"] == "project.created")
    review_created = next(event for event in audit_items if event["event_type"] == "review.created")
    assert project_created["tenant_id"] == tenant_id
    assert project_created["actor_id"] == owner_id
    assert project_created["actor_type"] == "user"
    assert project_created["request_id"] == "req-auth-owner"
    assert project_created["trace_id"] == "trace-auth-owner"
    assert review_created["actor_id"] == owner_id


def test_request_auth_headers_require_global_project_write_scope() -> None:
    client = TestClient(create_app())

    tenant_id = str(uuid4())
    principal_id = str(uuid4())
    limited_headers = {
        "X-Dros-Tenant-Id": tenant_id,
        "X-Dros-Actor-Id": principal_id,
        "X-Dros-Project-Role": "owner",
        "X-Dros-Scopes": "projects:read",
    }

    response = client.post(
        "/v1/projects",
        headers=limited_headers,
        json={
            "name": "Forbidden Project Create",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": principal_id,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "missing required scopes: projects:write"


def test_project_scope_effective_permissions_intersect_token_and_membership() -> None:
    client = TestClient(create_app())

    tenant_id = str(uuid4())
    owner_id = str(uuid4())
    reviewer_id = str(uuid4())
    owner_headers = {
        "X-Dros-Tenant-Id": tenant_id,
        "X-Dros-Actor-Id": owner_id,
        "X-Dros-Project-Role": "owner",
        "X-Dros-Scopes": "projects:read,projects:write,members:write,datasets:read,datasets:write",
    }
    reviewer_headers = {
        "X-Dros-Tenant-Id": tenant_id,
        "X-Dros-Actor-Id": reviewer_id,
        "X-Dros-Project-Role": "reviewer",
        "X-Dros-Scopes": "projects:read,datasets:read,datasets:write,reviews:read,reviews:write",
    }

    project_response = client.post(
        "/v1/projects",
        headers=owner_headers,
        json={
            "name": "Scoped Membership Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": owner_id,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    add_member_response = client.post(
        f"/v1/projects/{project_id}/members",
        headers=owner_headers,
        json={"principal_id": reviewer_id, "role": "reviewer"},
    )
    assert add_member_response.status_code == 201

    detail_response = client.get(f"/v1/projects/{project_id}", headers=reviewer_headers)
    assert detail_response.status_code == 200

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        headers=reviewer_headers,
        json={"accession": "TCGA-SCOPE-INTERSECTION", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 403
    assert dataset_response.json()["detail"] == "missing required project scopes: datasets:write"


def test_jwt_bearer_auth_enforces_token_validation_and_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "jwt-secret-for-tests-0123456789abcdef"
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://dev-idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()

    tenant_id = uuid4()
    principal_id = uuid4()
    token = jwt.encode(
        build_dev_jwt_claims(principal_id=principal_id, tenant_id=tenant_id),
        secret,
        algorithm="HS256",
    )
    client = TestClient(create_app())

    missing_bearer = client.get("/v1/session")
    assert missing_bearer.status_code == 401

    session_response = client.get(
        "/v1/session",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Request-Id": "req-jwt-auth",
            "X-Trace-Id": "trace-jwt-auth",
        },
    )
    assert session_response.status_code == 200
    session_payload = session_response.json()
    assert session_payload["tenant_id"] == str(tenant_id)
    assert session_payload["principal_id"] == str(principal_id)
    assert session_payload["scopes_json"]["auth_source"] == "jwt_bearer"

    project_response = client.post(
        "/v1/projects",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Request-Id": "req-jwt-auth",
            "X-Trace-Id": "trace-jwt-auth",
        },
        json={
            "name": "JWT Protected Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(principal_id),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    audit_response = client.get(
        f"/v1/projects/{project_id}/audit-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit_response.status_code == 200
    project_created = next(
        event
        for event in audit_response.json()["events"]["items"]
        if event["event_type"] == "project.created"
    )
    assert project_created["tenant_id"] == str(tenant_id)
    assert project_created["actor_id"] == str(principal_id)
    assert project_created["request_id"] == "req-jwt-auth"
    assert project_created["trace_id"] == "trace-jwt-auth"


def test_mixed_auth_mode_supports_bearer_and_dev_header_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "mixed-mode-secret-0123456789abcdef"
    monkeypatch.setenv("DROS_AUTH_MODE", "mixed")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://dev-idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()

    client = TestClient(create_app())
    dev_header_response = client.get(
        "/v1/session",
        headers={
            "X-Dros-Tenant-Id": str(uuid4()),
            "X-Dros-Principal-Id": str(uuid4()),
            "X-Dros-Project-Role": "reviewer",
            "X-Dros-Scopes": "projects:read,reviews:read",
        },
    )
    assert dev_header_response.status_code == 200
    assert dev_header_response.json()["scopes_json"]["auth_source"] == "headers"

    tenant_id = uuid4()
    principal_id = uuid4()
    token = jwt.encode(
        build_dev_jwt_claims(principal_id=principal_id, tenant_id=tenant_id),
        secret,
        algorithm="HS256",
    )
    bearer_response = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})
    assert bearer_response.status_code == 200
    assert bearer_response.json()["principal_id"] == str(principal_id)
    assert bearer_response.json()["scopes_json"]["auth_source"] == "jwt_bearer"


def test_invalid_jwt_bearer_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "valid-secret-0123456789abcdef012345"
    monkeypatch.setenv("DROS_AUTH_MODE", "jwt")
    monkeypatch.setenv("DROS_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DROS_AUTH_JWT_ALGORITHMS", "HS256")
    monkeypatch.setenv("DROS_AUTH_JWT_ISSUER", "https://dev-idp.dros.local")
    monkeypatch.setenv("DROS_AUTH_JWT_AUDIENCE", "dros-control-plane")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()

    bad_token = jwt.encode(
        {
            "sub": str(uuid4()),
            "principal_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "project_role": "owner",
            "scope": "projects:read",
            "iss": "https://dev-idp.dros.local",
            "aud": "dros-control-plane",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "wrong-secret-0123456789abcdef012345",
        algorithm="HS256",
    )
    client = TestClient(create_app())
    response = client.get("/v1/session", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
    assert response.json()["detail"].startswith("invalid bearer token:")


def test_gateway_event_stream_emits_structured_analysis_run_event() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Gateway Analysis Stream Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/gateway-analysis-stream.csv",
            "input_hash_sha256": "4" * 64,
            "row_count": 48,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    workflow_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["workflow"]["id"]

    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "workflow_instance_id": workflow_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 31,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    target_event = None
    with client.stream("GET", f"/v1/projects/{project_id}/events?once=true") as event_response:
        assert event_response.status_code == 200
        for line in event_response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line.removeprefix("data: "))
            if payload.get("event_name") == "analysis.run.succeeded":
                target_event = payload
                break

    assert target_event is not None
    assert target_event["produced_by"] == "runner"
    assert target_event["project_id"] == project_id
    assert target_event["idempotency_key"] == run_id
    assert target_event["payload"]["analysis_run_id"] == run_id
    assert target_event["payload"]["workflow_instance_id"] == workflow_id
    assert target_event["payload"]["output_artifact_count"] >= 5


def test_analysis_run_executes_inline_and_emits_artifacts() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Inline Runner Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/inline-runner.csv",
            "input_hash_sha256": "1" * 64,
            "row_count": 64,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    workflow_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["workflow"]["id"]

    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "workflow_instance_id": workflow_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 23,
        },
    )
    assert run_response.status_code == 202
    run = run_response.json()["analysis_run"]
    run_id = run["id"]
    assert run["state"] == "succeeded"
    assert run["started_at"] is not None
    assert run["finished_at"] is not None
    assert run["exit_code"] == 0
    assert run["runtime_manifest_json"]["job_broker"] == "in_memory"
    assert run["runtime_manifest_json"]["output_artifact_count"] >= 5

    run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{run_id}")
    assert run_detail.status_code == 200
    artifact_types = {artifact["artifact_type"] for artifact in run_detail.json()["artifacts"]}
    assert {"result_json", "table", "figure", "manifest", "log"} <= artifact_types

    workflow_detail = client.get(f"/v1/projects/{project_id}/workflows/{workflow_id}")
    assert workflow_detail.status_code == 200
    assert workflow_detail.json()["workflow"]["state"] == "analyzed"
    task_keys = {task["task_key"] for task in workflow_detail.json()["tasks"]}
    assert {"start", "analysis_run_dispatch", "analysis_run_execute", "artifact_emit"} <= task_keys

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    event_types = [event["event_type"] for event in audit_response.json()["events"]["items"]]
    assert "analysis.run.requested" in event_types
    assert "analysis.run.succeeded" in event_types
    assert "artifact.created" in event_types


def test_analysis_rerun_supersedes_prior_artifacts_and_records_lineage() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Analysis Rerun Lineage Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/rerun-lineage.csv",
            "input_hash_sha256": "8" * 64,
            "row_count": 72,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    workflow_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["workflow"]["id"]

    first_run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "workflow_instance_id": workflow_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 41,
        },
    )
    assert first_run_response.status_code == 202
    first_run_id = first_run_response.json()["analysis_run"]["id"]

    first_run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{first_run_id}")
    assert first_run_detail.status_code == 200
    first_artifacts = {
        (artifact["artifact_type"], artifact["output_slot"]): artifact
        for artifact in first_run_detail.json()["artifacts"]
    }
    assert len(first_artifacts) >= 5
    assert all(output_slot is not None for _, output_slot in first_artifacts)

    second_run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "workflow_instance_id": workflow_id,
            "rerun_of_run_id": first_run_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 43,
        },
    )
    assert second_run_response.status_code == 202
    second_run = second_run_response.json()["analysis_run"]
    second_run_id = second_run["id"]
    assert second_run["rerun_of_run_id"] == first_run_id
    assert second_run["runtime_manifest_json"]["rerun_of_run_id"] == first_run_id

    second_run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{second_run_id}")
    assert second_run_detail.status_code == 200
    second_artifacts = {
        (artifact["artifact_type"], artifact["output_slot"]): artifact
        for artifact in second_run_detail.json()["artifacts"]
    }
    assert first_artifacts.keys() == second_artifacts.keys()

    lineage_response = client.get(f"/v1/projects/{project_id}/lineage")
    assert lineage_response.status_code == 200
    supersede_edges = [
        edge
        for edge in lineage_response.json()["edges"]
        if edge["edge_type"] == "supersedes"
        and edge["from_kind"] == "artifact"
        and edge["to_kind"] == "artifact"
    ]
    assert len(supersede_edges) >= len(first_artifacts)

    for key, first_artifact in first_artifacts.items():
        second_artifact = second_artifacts[key]
        first_artifact_detail = client.get(f"/v1/projects/{project_id}/artifacts/{first_artifact['id']}")
        assert first_artifact_detail.status_code == 200
        assert first_artifact_detail.json()["artifact"]["superseded_by"] == second_artifact["id"]
        assert any(
            edge["from_id"] == first_artifact["id"] and edge["to_id"] == second_artifact["id"]
            for edge in supersede_edges
        )

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    run_request_events = [
        event
        for event in audit_response.json()["events"]["items"]
        if event["event_type"] == "analysis.run.requested"
    ]
    assert any(event["payload_json"]["rerun_of_run_id"] == first_run_id for event in run_request_events)
    assert "lineage.edge.created" in {event["event_type"] for event in audit_response.json()["events"]["items"]}


def test_analysis_rerun_rejects_incompatible_snapshot_or_template() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Analysis Rerun Compatibility Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_one_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/rerun-compatibility-1.csv",
            "input_hash_sha256": "7" * 64,
            "row_count": 24,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_one_response.status_code == 201
    snapshot_one_id = snapshot_one_response.json()["snapshot"]["id"]

    snapshot_two_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/rerun-compatibility-2.csv",
            "input_hash_sha256": "6" * 64,
            "row_count": 24,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_two_response.status_code == 201
    snapshot_two_id = snapshot_two_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    first_run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_one_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 5,
        },
    )
    assert first_run_response.status_code == 202
    first_run_id = first_run_response.json()["analysis_run"]["id"]

    incompatible_snapshot_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_two_id,
            "template_id": template_id,
            "rerun_of_run_id": first_run_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 11,
        },
    )
    assert incompatible_snapshot_response.status_code == 422
    assert "same snapshot_id" in incompatible_snapshot_response.json()["detail"]

    workflow_repository = dependencies.get_workflow_service().repository
    alternate_template_id = uuid4()
    workflow_repository.store.analysis_templates[alternate_template_id] = AnalysisTemplateRead(
        id=alternate_template_id,
        tenant_id=None,
        code="survival.km.v1",
        version="1.0.0",
        name="Kaplan-Meier Survival",
        image_digest="sha256:template-runner-survival-km-v1",
        script_hash="f" * 64,
        param_schema_json={"type": "object"},
        output_schema_json={"type": "object"},
        expected_outputs_json={"artifacts": ["result_json", "figure"]},
        doc_template_uri="object://templates/survival-km-v1.qmd",
        golden_dataset_uri="object://golden/survival-km-v1.csv",
        review_status=TemplateReviewStatus.APPROVED,
        approved_by=uuid4(),
        approved_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    incompatible_template_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_one_id,
            "template_id": str(alternate_template_id),
            "rerun_of_run_id": first_run_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 13,
        },
    )
    assert incompatible_template_response.status_code == 422
    assert "same template_id" in incompatible_template_response.json()["detail"]

    run_list_response = client.get(f"/v1/projects/{project_id}/analysis-runs")
    assert run_list_response.status_code == 200
    assert run_list_response.json()["items"]["page"]["total"] == 1


def test_analysis_rerun_skips_legacy_artifacts_without_output_slot() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Legacy Artifact Identity Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/legacy-artifact-identity.csv",
            "input_hash_sha256": "5" * 64,
            "row_count": 30,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    first_run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 17,
        },
    )
    assert first_run_response.status_code == 202
    first_run_id = first_run_response.json()["analysis_run"]["id"]

    first_run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{first_run_id}")
    assert first_run_detail.status_code == 200
    legacy_table = next(
        artifact
        for artifact in first_run_detail.json()["artifacts"]
        if artifact["artifact_type"] == "table"
    )

    workflow_repository = dependencies.get_workflow_service().repository
    legacy_table_id = legacy_table["id"]
    stored_legacy_table = workflow_repository.store.artifacts[UUID(legacy_table_id)]
    legacy_metadata = dict(stored_legacy_table.metadata_json)
    legacy_metadata.pop("output_slot", None)
    workflow_repository.store.artifacts[stored_legacy_table.id] = stored_legacy_table.model_copy(
        update={"output_slot": None, "metadata_json": legacy_metadata}
    )

    rerun_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "rerun_of_run_id": first_run_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 19,
        },
    )
    assert rerun_response.status_code == 202
    rerun_id = rerun_response.json()["analysis_run"]["id"]

    legacy_table_detail = client.get(f"/v1/projects/{project_id}/artifacts/{legacy_table_id}")
    assert legacy_table_detail.status_code == 200
    assert legacy_table_detail.json()["artifact"]["superseded_by"] is None

    rerun_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{rerun_id}")
    assert rerun_detail.status_code == 200
    rerun_table = next(
        artifact
        for artifact in rerun_detail.json()["artifacts"]
        if artifact["artifact_type"] == "table"
    )
    assert rerun_table["output_slot"] == "analysis.table.primary"

    lineage_response = client.get(f"/v1/projects/{project_id}/lineage")
    assert lineage_response.status_code == 200
    assert not any(
        edge["edge_type"] == "supersedes"
        and edge["from_id"] == legacy_table_id
        and edge["to_id"] == rerun_table["id"]
        for edge in lineage_response.json()["edges"]
    )


def test_analysis_run_preflight_failure_marks_run_failed() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Failed Runner Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/failed-runner.csv",
            "input_hash_sha256": "2" * 64,
            "row_count": 64,
            "column_schema_json": {"columns": ["os_time", "os_event"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    workflow_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["workflow"]["id"]

    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "workflow_instance_id": workflow_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 29,
        },
    )
    assert run_response.status_code == 202
    run = run_response.json()["analysis_run"]
    run_id = run["id"]
    assert run["state"] == "failed"
    assert run["exit_code"] == 66
    assert run["error_class"] == "PreflightValidationError"
    assert "missing required columns" in run["error_message_trunc"]

    run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{run_id}")
    assert run_detail.status_code == 200
    assert run_detail.json()["artifacts"] == []

    workflow_detail = client.get(f"/v1/projects/{project_id}/workflows/{workflow_id}")
    assert workflow_detail.status_code == 200
    assert workflow_detail.json()["workflow"]["state"] == "failed"
    task_keys = {task["task_key"] for task in workflow_detail.json()["tasks"]}
    assert {"start", "analysis_run_dispatch", "analysis_run_execute"} <= task_keys
    assert "artifact_emit" not in task_keys

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    event_types = [event["event_type"] for event in audit_response.json()["events"]["items"]]
    assert "analysis.run.requested" in event_types
    assert "analysis.run.failed" in event_types
    assert "analysis.run.succeeded" not in event_types


def test_workflow_child_branch_resume_creates_child_lineage_and_audit() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Workflow Child Branch Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    parent_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["workflow"]["id"]

    parent_advance = client.post(
        f"/v1/projects/{project_id}/workflows/{parent_id}/advance",
        json={},
    )
    assert parent_advance.status_code == 200
    assert parent_advance.json()["workflow"]["state"] == "retrieving"

    child_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={
            "workflow_type": "public_dataset_standard_analysis",
            "runtime_backend": "queue_workers",
            "parent_workflow_id": parent_id,
        },
    )
    assert child_response.status_code == 201
    child_workflow = child_response.json()["workflow"]
    child_id = child_workflow["id"]
    assert child_workflow["parent_workflow_id"] == parent_id
    assert child_workflow["state"] == "retrieving"
    assert child_workflow["current_step"] == "retrieving"

    child_detail = client.get(f"/v1/projects/{project_id}/workflows/{child_id}")
    assert child_detail.status_code == 200
    tasks = {task["task_key"]: task for task in child_detail.json()["tasks"]}
    assert tasks["start"]["state"] == "completed"
    assert tasks["start"]["output_payload_json"]["parent_workflow_id"] == parent_id
    assert tasks["resume_from_parent"]["state"] == "completed"
    assert tasks["resume_from_parent"]["input_payload_json"]["parent_workflow_id"] == parent_id
    assert tasks["resume_from_parent"]["input_payload_json"]["parent_state"] == "retrieving"

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    branch_event = next(
        event
        for event in audit_response.json()["events"]["items"]
        if event["event_type"] == "workflow.branch.created" and event["target_id"] == child_id
    )
    assert branch_event["payload_json"]["parent_workflow_id"] == parent_id
    assert branch_event["payload_json"]["child_initial_state"] == "retrieving"

    mismatch_child = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={
            "workflow_type": "evidence_backfill",
            "runtime_backend": "queue_workers",
            "parent_workflow_id": parent_id,
        },
    )
    assert mismatch_child.status_code == 422


def test_manuscript_version_base_version_no_clones_historical_blocks_and_links() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Manuscript Version Branch Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    manuscript_response = client.post(
        f"/v1/projects/{project_id}/manuscripts",
        json={"title": "Versioned Manuscript", "manuscript_type": "manuscript"},
    )
    assert manuscript_response.status_code == 201
    manuscript_id = manuscript_response.json()["manuscript"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/versioned/result.json",
            "sha256": "9" * 64,
            "metadata_json": {"kind": "version-source"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "versioned assertion",
            "numeric_payload_json": {"hazard_ratio": 0.65},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "versioned_source"},
            "claim_hash": "a" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]

    verify_assertion = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"target_ids": [assertion_id]},
    )
    assert verify_assertion.status_code == 202
    assert verify_assertion.json()["blocking_summary"] == []

    base_block_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "results",
            "block_order": 0,
            "block_type": "text",
            "content_md": "versioned assertion",
            "assertion_ids": [assertion_id],
        },
    )
    assert base_block_response.status_code == 201
    base_block_id = base_block_response.json()["block"]["id"]

    version_two_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/versions",
        json={"reason": "checkpoint current draft"},
    )
    assert version_two_response.status_code == 201
    assert version_two_response.json()["manuscript"]["current_version_no"] == 2

    version_two_blocks = client.get(f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks")
    assert version_two_blocks.status_code == 200
    assert len(version_two_blocks.json()["items"]) == 1
    assert version_two_blocks.json()["items"][0]["assertion_ids"] == [assertion_id]
    assert version_two_blocks.json()["items"][0]["supersedes_block_id"] == base_block_id

    version_one_blocks = client.get(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        params={"version_no": 1},
    )
    assert version_one_blocks.status_code == 200
    assert len(version_one_blocks.json()["items"]) == 1
    assert version_one_blocks.json()["items"][0]["id"] == base_block_id
    assert version_one_blocks.json()["items"][0]["version_no"] == 1

    extra_block_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "discussion",
            "block_order": 1,
            "block_type": "text",
            "content_md": "current draft only block",
            "assertion_ids": [],
        },
    )
    assert extra_block_response.status_code == 201

    version_three_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/versions",
        json={"base_version_no": 1, "reason": "rollback to version 1"},
    )
    assert version_three_response.status_code == 201
    assert version_three_response.json()["manuscript"]["current_version_no"] == 3

    version_three_blocks = client.get(f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks")
    assert version_three_blocks.status_code == 200
    current_blocks = version_three_blocks.json()["items"]
    assert len(current_blocks) == 1
    assert current_blocks[0]["content_md"] == "versioned assertion"
    assert current_blocks[0]["assertion_ids"] == [assertion_id]
    assert current_blocks[0]["supersedes_block_id"] == base_block_id

    version_two_snapshot = client.get(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        params={"version_no": 2},
    )
    assert version_two_snapshot.status_code == 200
    assert len(version_two_snapshot.json()["items"]) == 2
    assert {item["content_md"] for item in version_two_snapshot.json()["items"]} == {
        "versioned assertion",
        "current draft only block",
    }

    assertion_detail = client.get(f"/v1/projects/{project_id}/assertions/{assertion_id}")
    assert assertion_detail.status_code == 200
    assert len(assertion_detail.json()["block_links"]) == 3

    verify_manuscript = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"manuscript_id": manuscript_id},
    )
    assert verify_manuscript.status_code == 202
    assert verify_manuscript.json()["blocking_summary"] == []

    invalid_version = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/versions",
        json={"base_version_no": 99, "reason": "invalid future version"},
    )
    assert invalid_version.status_code == 422

    invalid_block_version = client.get(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        params={"version_no": 99},
    )
    assert invalid_block_version.status_code == 422

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    version_events = [
        event
        for event in audit_response.json()["events"]["items"]
        if event["event_type"] == "manuscript.version.created"
    ]
    assert len(version_events) == 2
    assert {event["payload_json"]["base_version_no"] for event in version_events} == {1}
    assert {event["payload_json"]["copied_block_count"] for event in version_events} == {1}


def test_evidence_and_export_routes_are_usable() -> None:
    client = TestClient(create_app())

    owner_id = str(uuid4())
    project_response = client.post(
        "/v1/projects",
        json={
            "name": "EGFR Evidence Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": owner_id,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    manuscript_response = client.post(
        f"/v1/projects/{project_id}/manuscripts",
        json={"title": "EGFR manuscript draft", "manuscript_type": "manuscript"},
    )
    assert manuscript_response.status_code == 201
    manuscript_id = manuscript_response.json()["manuscript"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/egfr.csv",
            "input_hash_sha256": "a" * 64,
            "row_count": 32,
            "column_schema_json": {"columns": ["os_time", "os_event", "marker"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "marker",
            },
            "random_seed": 1,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "run_id": run_id,
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/egfr/result.json",
            "sha256": "b" * 64,
            "metadata_json": {"kind": "cox_summary"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "egfr was associated with overall survival",
            "numeric_payload_json": {"hazard_ratio": 0.72, "p_value": 0.02},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "cox_summary"},
            "claim_hash": "c" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]
    assert assertion_response.json()["assertion"]["state"] == "draft"

    evidence_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "pubmed",
            "external_id_norm": "PMID:12345678",
            "title": "EGFR and overall survival in lung adenocarcinoma",
            "journal": "Journal of Thoracic Oncology",
            "pub_year": 2024,
            "pmid": "12345678",
            "pmcid": "PMC123456",
            "doi_norm": "10.1000/egfr-survival",
            "license_class": "pmc_oa_subset",
            "oa_subset_flag": True,
            "metadata_json": {"authors": ["Smith"]},
        },
    )
    assert evidence_response.status_code == 201
    evidence_source_id = evidence_response.json()["evidence_source"]["id"]

    list_sources = client.get(f"/v1/projects/{project_id}/evidence")
    assert list_sources.status_code == 200
    assert list_sources.json()["items"]["page"]["total"] == 1

    search_response = client.post(
        f"/v1/projects/{project_id}/evidence/search",
        json={"query": "EGFR survival"},
    )
    assert search_response.status_code == 202
    assert search_response.json()["results"][0]["pmid"] == "12345678"

    resolve_response = client.post(
        f"/v1/projects/{project_id}/evidence/resolve",
        json={"identifiers": ["12345678", "PMC404404"]},
    )
    assert resolve_response.status_code == 200
    assert [item["pmid"] for item in resolve_response.json()["resolved"]] == ["12345678"]
    assert resolve_response.json()["unresolved"] == ["PMC404404"]

    link_response = client.post(
        f"/v1/projects/{project_id}/evidence-links",
        json={
            "assertion_id": assertion_id,
            "evidence_source_id": evidence_source_id,
            "relation_type": "supports",
            "source_span_start": 10,
            "source_span_end": 42,
            "confidence": 0.9,
        },
    )
    assert link_response.status_code == 201
    link_id = link_response.json()["evidence_link"]["id"]
    assert link_response.json()["evidence_link"]["verifier_status"] == "pending"

    list_links = client.get(f"/v1/projects/{project_id}/evidence-links")
    assert list_links.status_code == 200
    assert list_links.json()["items"]["page"]["total"] == 1
    assert list_links.json()["items"]["items"][0]["id"] == link_id

    verify_response = client.post(f"/v1/projects/{project_id}/evidence-links/{link_id}/verify")
    assert verify_response.status_code == 200
    assert verify_response.json()["evidence_link"]["verifier_status"] == "passed"

    block_before_verify = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "results",
            "block_order": 0,
            "block_type": "text",
            "content_md": "EGFR was associated with overall survival.",
            "assertion_ids": [assertion_id],
        },
    )
    assert block_before_verify.status_code == 422

    assertion_verify_response = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"target_ids": [assertion_id]},
    )
    assert assertion_verify_response.status_code == 202
    assert assertion_verify_response.json()["blocking_summary"] == []

    block_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "results",
            "block_order": 0,
            "block_type": "text",
            "content_md": "EGFR was associated with overall survival.",
            "assertion_ids": [assertion_id],
        },
    )
    assert block_response.status_code == 201

    export_before_manuscript_verify = client.post(
        f"/v1/projects/{project_id}/exports",
        json={"manuscript_id": manuscript_id, "format": "docx"},
    )
    assert export_before_manuscript_verify.status_code == 202
    assert export_before_manuscript_verify.json()["export_job"]["state"] == "blocked"

    manuscript_verify_response = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"manuscript_id": manuscript_id},
    )
    assert manuscript_verify_response.status_code == 202
    assert manuscript_verify_response.json()["blocking_summary"] == []
    gate_names = {item["gate_name"] for item in manuscript_verify_response.json()["gate_evaluations"]}
    assert {
        "citation_resolver",
        "claim_evidence_binder",
        "data_consistency_checker",
        "license_guard",
    } <= gate_names
    verification_workflow_id = manuscript_verify_response.json()["workflow_instance_id"]

    verification_workflow = client.get(f"/v1/projects/{project_id}/workflows/{verification_workflow_id}")
    assert verification_workflow.status_code == 200
    assert verification_workflow.json()["workflow"]["state"] == "approved"
    assert len(verification_workflow.json()["gate_evaluations"]) == len(
        manuscript_verify_response.json()["gate_evaluations"]
    )
    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    gate_audits = [
        event
        for event in audit_response.json()["events"]["items"]
        if event["event_type"] == "evidence_control_plane.gate_evaluated"
    ]
    assert gate_audits
    assert {event["payload_json"]["gate_name"] for event in gate_audits} >= {
        "citation_resolver",
        "claim_evidence_binder",
        "data_consistency_checker",
        "license_guard",
    }

    export_response = client.post(
        f"/v1/projects/{project_id}/exports",
        json={"manuscript_id": manuscript_id, "format": "docx"},
    )
    assert export_response.status_code == 202
    export_job = export_response.json()["export_job"]
    assert export_job["state"] == "completed"
    export_job_id = export_job["id"]

    export_list = client.get(f"/v1/projects/{project_id}/exports")
    assert export_list.status_code == 200
    assert export_list.json()["items"]["page"]["total"] == 2
    assert export_list.json()["items"]["items"][0]["id"] == export_job_id

    export_detail = client.get(f"/v1/projects/{project_id}/exports/{export_job_id}")
    assert export_detail.status_code == 200
    assert export_detail.json()["output_artifact"]["artifact_type"] == "docx"

    export_audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert export_audit_response.status_code == 200
    export_event_types = {event["event_type"] for event in export_audit_response.json()["events"]["items"]}
    assert "export.completed" in export_event_types


def test_review_audit_and_workflow_transition_guardrails() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Workflow Guardrail Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    workflow_response = client.post(
        f"/v1/projects/{project_id}/workflows",
        json={"workflow_type": "public_dataset_standard_analysis", "runtime_backend": "queue_workers"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["workflow"]["id"]

    invalid_transition = client.post(
        f"/v1/projects/{project_id}/workflows/{workflow_id}/advance",
        json={"action": "export"},
    )
    assert invalid_transition.status_code == 422

    advance_response = client.post(
        f"/v1/projects/{project_id}/workflows/{workflow_id}/advance",
        json={},
    )
    assert advance_response.status_code == 200
    assert advance_response.json()["workflow"]["state"] == "retrieving"

    review_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        json={
            "review_type": "manuscript",
            "target_kind": "project",
            "target_id": project_id,
            "comments": "ready for manual review",
        },
    )
    assert review_response.status_code == 201
    review_id = review_response.json()["review"]["id"]

    decision_response = client.post(
        f"/v1/projects/{project_id}/reviews/{review_id}/decisions",
        json={"action": "approve", "comments": "approved"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["review"]["state"] == "approved"

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    event_types = {event["event_type"] for event in audit_response.json()["events"]["items"]}
    assert "review.created" in event_types
    assert "review.requested" in event_types
    assert "review.decision.recorded" in event_types
    assert "review.completed" in event_types


def test_manuscript_reviews_are_version_scoped_and_emitted_to_gateway() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Version Scoped Reviews",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    manuscript_response = client.post(
        f"/v1/projects/{project_id}/manuscripts",
        json={
            "title": "Scoped Review Manuscript",
            "manuscript_type": "manuscript",
            "style_profile_json": {},
        },
    )
    assert manuscript_response.status_code == 201
    manuscript_id = manuscript_response.json()["manuscript"]["id"]

    current_review_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        json={
            "review_type": "manuscript",
            "target_kind": "manuscript",
            "target_id": manuscript_id,
            "comments": "current draft review",
        },
    )
    assert current_review_response.status_code == 201
    current_review = current_review_response.json()["review"]
    assert current_review["target_version_no"] == 1

    project_detail_response = client.get(f"/v1/projects/{project_id}")
    assert project_detail_response.status_code == 200
    assert project_detail_response.json()["review_summary"] == {"pending": 1}
    assert project_detail_response.json()["review_summary_scope"] == {
        "target_kind": "manuscript",
        "target_id": manuscript_id,
        "target_version_no": 1,
        "label": "Scoped Review Manuscript",
    }

    version_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/versions",
        json={
            "base_version_no": 1,
            "reason": "fork a new draft",
        },
    )
    assert version_response.status_code == 201
    assert version_response.json()["manuscript"]["current_version_no"] == 2

    project_detail_response = client.get(f"/v1/projects/{project_id}")
    assert project_detail_response.status_code == 200
    assert project_detail_response.json()["review_summary"] == {}
    assert project_detail_response.json()["review_summary_scope"] == {
        "target_kind": "manuscript",
        "target_id": manuscript_id,
        "target_version_no": 2,
        "label": "Scoped Review Manuscript",
    }

    historical_review_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        json={
            "review_type": "manuscript",
            "target_kind": "manuscript",
            "target_id": manuscript_id,
            "target_version_no": 1,
            "comments": "historical version review",
        },
    )
    assert historical_review_response.status_code == 201
    historical_review = historical_review_response.json()["review"]
    assert historical_review["target_version_no"] == 1

    project_detail_response = client.get(f"/v1/projects/{project_id}")
    assert project_detail_response.status_code == 200
    assert project_detail_response.json()["review_summary"] == {}
    assert project_detail_response.json()["review_summary_scope"] == {
        "target_kind": "manuscript",
        "target_id": manuscript_id,
        "target_version_no": 2,
        "label": "Scoped Review Manuscript",
    }

    current_v2_review_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        json={
            "review_type": "manuscript",
            "target_kind": "manuscript",
            "target_id": manuscript_id,
            "comments": "current v2 review",
        },
    )
    assert current_v2_review_response.status_code == 201
    current_v2_review = current_v2_review_response.json()["review"]
    assert current_v2_review["target_version_no"] == 2

    project_detail_response = client.get(f"/v1/projects/{project_id}")
    assert project_detail_response.status_code == 200
    assert project_detail_response.json()["review_summary"] == {"pending": 1}
    assert project_detail_response.json()["review_summary_scope"] == {
        "target_kind": "manuscript",
        "target_id": manuscript_id,
        "target_version_no": 2,
        "label": "Scoped Review Manuscript",
    }

    future_review_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        json={
            "review_type": "manuscript",
            "target_kind": "manuscript",
            "target_id": manuscript_id,
            "target_version_no": 3,
        },
    )
    assert future_review_response.status_code == 422
    assert "ahead of manuscript current_version_no 2" in future_review_response.json()["detail"]

    invalid_target_response = client.post(
        f"/v1/projects/{project_id}/reviews",
        json={
            "review_type": "analysis",
            "target_kind": "project",
            "target_id": project_id,
            "target_version_no": 1,
        },
    )
    assert invalid_target_response.status_code == 422
    assert invalid_target_response.json()["detail"] == "target_version_no is only supported for manuscript reviews"

    decision_response = client.post(
        f"/v1/projects/{project_id}/reviews/{historical_review['id']}/decisions",
        json={"action": "approve", "comments": "historical version approved"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["review"]["target_version_no"] == 1

    project_detail_response = client.get(f"/v1/projects/{project_id}")
    assert project_detail_response.status_code == 200
    assert project_detail_response.json()["review_summary"] == {"pending": 1}
    assert project_detail_response.json()["review_summary_scope"] == {
        "target_kind": "manuscript",
        "target_id": manuscript_id,
        "target_version_no": 2,
        "label": "Scoped Review Manuscript",
    }

    reviews_response = client.get(f"/v1/projects/{project_id}/reviews")
    assert reviews_response.status_code == 200
    reviews = reviews_response.json()["items"]["items"]
    assert reviews[0]["target_version_no"] == 2
    assert reviews[1]["target_version_no"] == 1

    audit_response = client.get(f"/v1/projects/{project_id}/audit-events")
    assert audit_response.status_code == 200
    historical_audits = [
        event
        for event in audit_response.json()["events"]["items"]
        if event["target_id"] == historical_review["id"] and event["event_type"].startswith("review.")
    ]
    assert {event["event_type"] for event in historical_audits} >= {
        "review.created",
        "review.requested",
        "review.decision.recorded",
        "review.completed",
    }
    for event in historical_audits:
        assert event["payload_json"].get("target_version_no") == 1

    streamed_events: list[dict[str, object]] = []
    with client.stream("GET", f"/v1/projects/{project_id}/events?once=true") as event_response:
        assert event_response.status_code == 200
        for line in event_response.iter_lines():
            if line.startswith("data: "):
                streamed_events.append(json.loads(line.removeprefix("data: ")))

    requested_event = next(
        event
        for event in streamed_events
        if event["event_name"] == "review.requested" and event["payload"]["review_id"] == historical_review["id"]
    )
    assert requested_event["payload"]["target_version_no"] == 1

    completed_event = next(
        event
        for event in streamed_events
        if event["event_name"] == "review.completed" and event["payload"]["review_id"] == historical_review["id"]
    )
    assert completed_event["payload"]["target_version_no"] == 1


def test_evidence_search_falls_back_to_ncbi_on_cache_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_NCBI_ENABLED", "true")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()
    remote_calls = {"count": 0}

    def fake_search_remote(self, query: str, *, max_results: int) -> list[NCBIEvidenceRecord]:
        remote_calls["count"] += 1
        assert query == "ALK fusion prognosis"
        assert max_results == 5
        return [
            NCBIEvidenceRecord(
                pmid="55555555",
                pmcid="PMC5555555",
                doi="10.1000/alk-prognosis",
                title="ALK fusion prognosis in lung adenocarcinoma",
                journal="Journal of Precision Oncology",
                year=2025,
                license_class=LicenseClass.PMC_OA_SUBSET,
                oa_subset_flag=True,
                match_reason="ncbi_entrez_search",
                dedupe_key="PMID:55555555",
                metadata_json={"authors": ["Chen"]},
            )
        ]

    monkeypatch.setattr(NCBIAdapter, "_search_remote", fake_search_remote)

    client = TestClient(create_app())
    project_response = client.post(
        "/v1/projects",
        json={
            "name": "NCBI Search Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    first_search = client.post(
        f"/v1/projects/{project_id}/evidence/search",
        json={"query": "ALK fusion prognosis", "filters": {"max_results": 5}},
    )
    assert first_search.status_code == 202
    assert first_search.json()["results"][0]["pmid"] == "55555555"
    assert first_search.json()["results"][0]["license_class"] == "pmc_oa_subset"

    second_search = client.post(
        f"/v1/projects/{project_id}/evidence/search",
        json={"query": "ALK fusion prognosis", "filters": {"max_results": 5}},
    )
    assert second_search.status_code == 202
    assert second_search.json()["results"][0]["dedupe_key"] == "PMID:55555555"
    assert remote_calls["count"] == 1


def test_evidence_search_external_first_prefers_ncbi_and_merges_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_NCBI_ENABLED", "true")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()
    remote_calls = {"count": 0}

    def fake_search_remote(self, query: str, *, max_results: int) -> list[NCBIEvidenceRecord]:
        remote_calls["count"] += 1
        assert query == "EGFR survival"
        assert max_results == 5
        return [
            NCBIEvidenceRecord(
                pmid="77777777",
                pmcid="PMC7777777",
                doi="10.1000/egfr-external",
                title="External EGFR survival evidence",
                journal="Journal of External Evidence",
                year=2026,
                license_class=LicenseClass.PMC_OA_SUBSET,
                oa_subset_flag=True,
                match_reason="ncbi_entrez_search",
                dedupe_key="PMID:77777777",
                metadata_json={"authors": ["Li"]},
            )
        ]

    monkeypatch.setattr(NCBIAdapter, "_search_remote", fake_search_remote)

    client = TestClient(create_app())
    project_response = client.post(
        "/v1/projects",
        json={
            "name": "NCBI External First Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    evidence_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "pubmed",
            "external_id_norm": "PMID:12345678",
            "title": "Cached EGFR survival evidence",
            "journal": "Journal of Cached Evidence",
            "pub_year": 2024,
            "pmid": "12345678",
            "pmcid": "PMC123456",
            "doi_norm": "10.1000/egfr-cached",
            "license_class": "pmc_oa_subset",
            "oa_subset_flag": True,
            "metadata_json": {"authors": ["Smith"]},
        },
    )
    assert evidence_response.status_code == 201

    search_response = client.post(
        f"/v1/projects/{project_id}/evidence/search",
        json={"query": "EGFR survival", "filters": {"max_results": 5, "search_scope": "external_first"}},
    )
    assert search_response.status_code == 202
    assert [item["pmid"] for item in search_response.json()["results"]] == ["77777777", "12345678"]
    assert remote_calls["count"] == 1

    second_search = client.post(
        f"/v1/projects/{project_id}/evidence/search",
        json={"query": "EGFR survival", "filters": {"max_results": 5, "search_scope": "external_first"}},
    )
    assert second_search.status_code == 202
    assert [item["pmid"] for item in second_search.json()["results"]] == ["77777777", "12345678"]
    assert remote_calls["count"] == 1


def test_evidence_search_project_cache_only_skips_ncbi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_NCBI_ENABLED", "true")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()
    remote_calls = {"count": 0}

    def fake_search_remote(self, query: str, *, max_results: int) -> list[NCBIEvidenceRecord]:
        remote_calls["count"] += 1
        return []

    monkeypatch.setattr(NCBIAdapter, "_search_remote", fake_search_remote)

    client = TestClient(create_app())
    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Project Cache Only Search",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    search_response = client.post(
        f"/v1/projects/{project_id}/evidence/search",
        json={"query": "BRAF resistance", "filters": {"search_scope": "project_cache_only"}},
    )
    assert search_response.status_code == 202
    assert search_response.json()["results"] == []
    assert remote_calls["count"] == 0


def test_evidence_resolve_fetches_external_source_and_binds_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DROS_NCBI_ENABLED", "true")
    get_settings.cache_clear()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()
    remote_calls = {"count": 0}

    def fake_resolve_remote(self, identifier: str) -> NCBIEvidenceRecord | None:
        remote_calls["count"] += 1
        assert identifier == "PMC7654321"
        return NCBIEvidenceRecord(
            pmid="66666666",
            pmcid="PMC7654321",
            doi="10.1000/pmc-resolve",
            title="External NCBI resolved evidence",
            journal="Open Evidence",
            year=2024,
            license_class=LicenseClass.PMC_OA_SUBSET,
            oa_subset_flag=True,
            match_reason="ncbi_identifier_resolve",
            dedupe_key="PMID:66666666",
            metadata_json={"authors": ["Wang"]},
        )

    monkeypatch.setattr(NCBIAdapter, "_resolve_remote", fake_resolve_remote)

    client = TestClient(create_app())
    project_response = client.post(
        "/v1/projects",
        json={
            "name": "NCBI Resolve Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    first_resolve = client.post(
        f"/v1/projects/{project_id}/evidence/resolve",
        json={"identifiers": ["PMC7654321"]},
    )
    assert first_resolve.status_code == 200
    assert first_resolve.json()["resolved"][0]["pmcid"] == "PMC7654321"
    assert first_resolve.json()["resolved"][0]["license_class"] == "pmc_oa_subset"

    second_resolve = client.post(
        f"/v1/projects/{project_id}/evidence/resolve",
        json={"identifiers": ["PMC7654321"]},
    )
    assert second_resolve.status_code == 200
    assert second_resolve.json()["resolved"][0]["pmid"] == "66666666"
    assert remote_calls["count"] == 1

    list_sources = client.get(f"/v1/projects/{project_id}/evidence")
    assert list_sources.status_code == 200
    assert list_sources.json()["items"]["page"]["total"] == 1


def test_license_guard_blocks_metadata_only_span_evidence() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "License Guard Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    manuscript_response = client.post(
        f"/v1/projects/{project_id}/manuscripts",
        json={"title": "License constrained manuscript", "manuscript_type": "manuscript"},
    )
    assert manuscript_response.status_code == 201
    manuscript_id = manuscript_response.json()["manuscript"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/license.csv",
            "input_hash_sha256": "d" * 64,
            "row_count": 8,
            "column_schema_json": {"columns": ["os_time", "os_event", "marker"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "marker",
            },
            "random_seed": 11,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "run_id": run_id,
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/license/result.json",
            "sha256": "e" * 64,
            "metadata_json": {"kind": "cox_summary"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "marker associated with overall survival",
            "numeric_payload_json": {"hazard_ratio": 0.71},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "cox_summary"},
            "claim_hash": "f" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]

    assertion_verify = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"target_ids": [assertion_id]},
    )
    assert assertion_verify.status_code == 202
    assert assertion_verify.json()["blocking_summary"] == []

    block_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "results",
            "block_order": 0,
            "block_type": "text",
            "content_md": "Marker associated with overall survival.",
            "assertion_ids": [assertion_id],
        },
    )
    assert block_response.status_code == 201

    evidence_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "pubmed",
            "external_id_norm": "PMID:99999999",
            "title": "Restricted full text evidence",
            "journal": "Evidence Journal",
            "pub_year": 2025,
            "pmid": "99999999",
            "license_class": "metadata_only",
            "oa_subset_flag": False,
            "metadata_json": {"authors": ["Lee"]},
        },
    )
    assert evidence_response.status_code == 201
    evidence_source_id = evidence_response.json()["evidence_source"]["id"]

    evidence_link_response = client.post(
        f"/v1/projects/{project_id}/evidence-links",
        json={
            "assertion_id": assertion_id,
            "evidence_source_id": evidence_source_id,
            "relation_type": "supports",
            "source_span_start": 5,
            "source_span_end": 25,
            "confidence": 0.8,
        },
    )
    assert evidence_link_response.status_code == 201
    link_id = evidence_link_response.json()["evidence_link"]["id"]

    evidence_link_verify = client.post(f"/v1/projects/{project_id}/evidence-links/{link_id}/verify")
    assert evidence_link_verify.status_code == 200
    assert evidence_link_verify.json()["evidence_link"]["verifier_status"] == "blocked"

    manuscript_verify = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"manuscript_id": manuscript_id},
    )
    assert manuscript_verify.status_code == 202
    assert "metadata_only cannot support excerpt or span binding" in " ".join(manuscript_verify.json()["blocking_summary"])
    license_gate = next(
        item for item in manuscript_verify.json()["gate_evaluations"] if item["gate_name"] == "license_guard"
    )
    assert license_gate["status"] == "blocked"

    export_response = client.post(
        f"/v1/projects/{project_id}/exports",
        json={"manuscript_id": manuscript_id, "format": "docx"},
    )
    assert export_response.status_code == 202
    assert export_response.json()["export_job"]["state"] == "blocked"


def test_gateway_emits_structured_assertion_and_evidence_events() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Structured Evidence Events Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/structured-events/result.json",
            "mime_type": "application/json",
            "sha256": "d" * 64,
            "metadata_json": {"kind": "cox_summary"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "egfr associated with overall survival",
            "numeric_payload_json": {"hazard_ratio": 0.65},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "$.hazard_ratio"},
            "claim_hash": "e" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]

    passing_source_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "pubmed",
            "external_id_norm": "PMID:12345678",
            "title": "Passing Evidence",
            "journal": "Evidence Journal",
            "pub_year": 2025,
            "pmid": "12345678",
            "license_class": "public",
            "oa_subset_flag": False,
            "metadata_json": {"authors": ["Smith"]},
        },
    )
    assert passing_source_response.status_code == 201
    passing_source_id = passing_source_response.json()["evidence_source"]["id"]

    passing_link_response = client.post(
        f"/v1/projects/{project_id}/evidence-links",
        json={
            "assertion_id": assertion_id,
            "evidence_source_id": passing_source_id,
            "relation_type": "supports",
            "source_span_start": 10,
            "source_span_end": 40,
            "confidence": 0.9,
        },
    )
    assert passing_link_response.status_code == 201
    passing_link_id = passing_link_response.json()["evidence_link"]["id"]

    passing_verify_response = client.post(f"/v1/projects/{project_id}/evidence-links/{passing_link_id}/verify")
    assert passing_verify_response.status_code == 200
    assert passing_verify_response.json()["evidence_link"]["verifier_status"] == "passed"

    blocked_source_response = client.post(
        f"/v1/projects/{project_id}/evidence",
        json={
            "source_type": "pubmed",
            "external_id_norm": "PMID:99999999",
            "title": "Blocked Evidence",
            "journal": "Evidence Journal",
            "pub_year": 2025,
            "pmid": "99999999",
            "license_class": "metadata_only",
            "oa_subset_flag": False,
            "metadata_json": {"authors": ["Lee"]},
        },
    )
    assert blocked_source_response.status_code == 201
    blocked_source_id = blocked_source_response.json()["evidence_source"]["id"]

    blocked_link_response = client.post(
        f"/v1/projects/{project_id}/evidence-links",
        json={
            "assertion_id": assertion_id,
            "evidence_source_id": blocked_source_id,
            "relation_type": "supports",
            "source_span_start": 5,
            "source_span_end": 25,
            "confidence": 0.8,
        },
    )
    assert blocked_link_response.status_code == 201
    blocked_link_id = blocked_link_response.json()["evidence_link"]["id"]

    blocked_verify_response = client.post(f"/v1/projects/{project_id}/evidence-links/{blocked_link_id}/verify")
    assert blocked_verify_response.status_code == 200
    assert blocked_verify_response.json()["evidence_link"]["verifier_status"] == "blocked"

    streamed_events: list[dict[str, object]] = []
    with client.stream("GET", f"/v1/projects/{project_id}/events?once=true") as event_response:
        assert event_response.status_code == 200
        for line in event_response.iter_lines():
            if line.startswith("data: "):
                streamed_events.append(json.loads(line.removeprefix("data: ")))

    assertion_event = next(
        event
        for event in streamed_events
        if event["event_name"] == "assertion.created" and event["payload"]["assertion_id"] == assertion_id
    )
    assert assertion_event["produced_by"] == "manuscript_service"
    assert assertion_event["payload"]["state"] == "draft"
    assert assertion_event["payload"]["source_artifact_id"] == artifact_id

    linked_event = next(
        event
        for event in streamed_events
        if event["event_name"] == "evidence.linked" and event["payload"]["evidence_link_id"] == passing_link_id
    )
    assert linked_event["produced_by"] == "evidence_service"
    assert linked_event["payload"]["assertion_id"] == assertion_id
    assert linked_event["payload"]["evidence_source_id"] == passing_source_id
    assert linked_event["payload"]["relation_type"] == "supports"
    assert linked_event["payload"]["verifier_status"] == "passed"

    blocked_event = next(
        event
        for event in streamed_events
        if event["event_name"] == "evidence.blocked" and event["payload"]["candidate_identifier"] == "PMID:99999999"
    )
    assert blocked_event["produced_by"] == "evidence_service"
    assert blocked_event["payload"]["assertion_id"] == assertion_id
    assert "metadata_only cannot support excerpt or span binding" in blocked_event["payload"]["reason"]
    assert any(
        "metadata_only cannot support excerpt or span binding" in item
        for item in blocked_event["payload"]["needs_human_items"]
    )


def test_superseded_artifact_breaks_verification_chain() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Broken Chain Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    manuscript_response = client.post(
        f"/v1/projects/{project_id}/manuscripts",
        json={"title": "Broken chain manuscript", "manuscript_type": "manuscript"},
    )
    assert manuscript_response.status_code == 201
    manuscript_id = manuscript_response.json()["manuscript"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/broken-chain.csv",
            "input_hash_sha256": "1" * 64,
            "row_count": 16,
            "column_schema_json": {"columns": ["os_time", "os_event", "marker"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "marker",
            },
            "random_seed": 13,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    run_detail_response = client.get(f"/v1/projects/{project_id}/analysis-runs/{run_id}")
    assert run_detail_response.status_code == 200
    original_artifact = next(
        artifact
        for artifact in run_detail_response.json()["artifacts"]
        if artifact["artifact_type"] == "result_json"
    )
    original_artifact_id = original_artifact["id"]

    assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "marker associated with progression free survival",
            "numeric_payload_json": {"hazard_ratio": 0.61},
            "source_artifact_id": original_artifact_id,
            "source_span_json": {"path": "cox_summary"},
            "claim_hash": "3" * 64,
        },
    )
    assert assertion_response.status_code == 201
    assertion_id = assertion_response.json()["assertion"]["id"]

    assertion_verify = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"target_ids": [assertion_id]},
    )
    assert assertion_verify.status_code == 202
    assert assertion_verify.json()["blocking_summary"] == []

    block_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "results",
            "block_order": 0,
            "block_type": "text",
            "content_md": "Marker associated with progression free survival.",
            "assertion_ids": [assertion_id],
        },
    )
    assert block_response.status_code == 201

    replacement_artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/broken-chain/replacement.json",
            "sha256": "4" * 64,
            "metadata_json": {
                "kind": "cox_summary_v2",
                "output_slot": "analysis.result.primary",
            },
        },
    )
    assert replacement_artifact_response.status_code == 201
    replacement_artifact_id = replacement_artifact_response.json()["artifact"]["id"]

    supersede_response = client.post(
        f"/v1/projects/{project_id}/lineage-edges",
        json={
            "from_kind": "artifact",
            "from_id": original_artifact_id,
            "edge_type": "supersedes",
            "to_kind": "artifact",
            "to_id": replacement_artifact_id,
        },
    )
    assert supersede_response.status_code == 201

    manuscript_verify = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"manuscript_id": manuscript_id},
    )
    assert manuscript_verify.status_code == 202
    assert "source artifact was superseded" in " ".join(manuscript_verify.json()["blocking_summary"])
    binder_gate = next(
        item
        for item in manuscript_verify.json()["gate_evaluations"]
        if item["gate_name"] == "claim_evidence_binder" and item["target_kind"] == "manuscript"
    )
    assert binder_gate["status"] == "blocked"

    export_response = client.post(
        f"/v1/projects/{project_id}/exports",
        json={"manuscript_id": manuscript_id, "format": "docx"},
    )
    assert export_response.status_code == 202
    assert export_response.json()["export_job"]["state"] == "blocked"


def test_manual_artifact_supersedes_rejects_mismatched_output_slot() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Mismatched Output Slot Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    original_artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "output_slot": "analysis.result.primary",
            "storage_uri": "object://artifacts/manual-supersede/original.json",
            "sha256": "1" * 64,
            "metadata_json": {},
        },
    )
    assert original_artifact_response.status_code == 201
    original_artifact_id = original_artifact_response.json()["artifact"]["id"]

    replacement_artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "output_slot": "analysis.result.secondary",
            "storage_uri": "object://artifacts/manual-supersede/replacement.json",
            "sha256": "2" * 64,
            "metadata_json": {},
        },
    )
    assert replacement_artifact_response.status_code == 201
    replacement_artifact_id = replacement_artifact_response.json()["artifact"]["id"]

    supersede_response = client.post(
        f"/v1/projects/{project_id}/lineage-edges",
        json={
            "from_kind": "artifact",
            "from_id": original_artifact_id,
            "edge_type": "supersedes",
            "to_kind": "artifact",
            "to_id": replacement_artifact_id,
        },
    )
    assert supersede_response.status_code == 422
    assert "matching output_slot" in supersede_response.json()["detail"]


def test_manual_artifact_supersedes_rejects_unrelated_run_outputs() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Unrelated Run Supersede Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/unrelated-runs.csv",
            "input_hash_sha256": "7" * 64,
            "row_count": 12,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    first_run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 3,
        },
    )
    assert first_run_response.status_code == 202
    first_run_id = first_run_response.json()["analysis_run"]["id"]

    second_run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 9,
        },
    )
    assert second_run_response.status_code == 202
    second_run_id = second_run_response.json()["analysis_run"]["id"]

    first_run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{first_run_id}")
    assert first_run_detail.status_code == 200
    first_result_artifact_id = next(
        artifact["id"]
        for artifact in first_run_detail.json()["artifacts"]
        if artifact["artifact_type"] == "result_json"
    )

    second_run_detail = client.get(f"/v1/projects/{project_id}/analysis-runs/{second_run_id}")
    assert second_run_detail.status_code == 200
    second_result_artifact_id = next(
        artifact["id"]
        for artifact in second_run_detail.json()["artifacts"]
        if artifact["artifact_type"] == "result_json"
    )

    supersede_response = client.post(
        f"/v1/projects/{project_id}/lineage-edges",
        json={
            "from_kind": "artifact",
            "from_id": first_result_artifact_id,
            "edge_type": "supersedes",
            "to_kind": "artifact",
            "to_id": second_result_artifact_id,
        },
    )
    assert supersede_response.status_code == 422
    assert "replacement run to declare rerun_of_run_id" in supersede_response.json()["detail"]


def test_create_artifact_rejects_duplicate_output_slot_within_run() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Duplicate Output Slot Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/duplicate-output-slot.csv",
            "input_hash_sha256": "8" * 64,
            "row_count": 14,
            "column_schema_json": {"columns": ["os_time", "os_event", "risk_group"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
            },
            "random_seed": 21,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    duplicate_artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "run_id": run_id,
            "artifact_type": "result_json",
            "output_slot": "analysis.result.primary",
            "storage_uri": "object://artifacts/duplicate-output-slot/result-duplicate.json",
            "sha256": "3" * 64,
            "metadata_json": {
                "kind": "manual_duplicate",
            },
        },
    )
    assert duplicate_artifact_response.status_code == 409
    assert "artifact output_slot analysis.result.primary already exists" in duplicate_artifact_response.json()["detail"]


def test_create_artifact_legacy_metadata_output_slot_backfills_formal_field() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Legacy Output Slot Compatibility Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/legacy-output-slot/result.json",
            "sha256": "5" * 64,
            "metadata_json": {
                "output_slot": "analysis.result.primary",
                "kind": "legacy_payload",
            },
        },
    )
    assert artifact_response.status_code == 201
    artifact = artifact_response.json()["artifact"]
    assert artifact["output_slot"] == "analysis.result.primary"
    assert artifact["metadata_json"]["output_slot"] == "analysis.result.primary"


def test_create_artifact_rejects_output_slot_mismatch_between_top_level_and_metadata() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Output Slot Mismatch Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "artifact_type": "result_json",
            "output_slot": "analysis.result.primary",
            "storage_uri": "object://artifacts/output-slot-mismatch/result.json",
            "sha256": "6" * 64,
            "metadata_json": {
                "output_slot": "analysis.result.secondary",
            },
        },
    )
    assert artifact_response.status_code == 422
    assert "output_slot mismatch" in artifact_response.json()["detail"]


def test_dangling_assertion_blocks_manuscript_verification() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Dangling Assertion Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    manuscript_response = client.post(
        f"/v1/projects/{project_id}/manuscripts",
        json={"title": "Dangling assertion manuscript", "manuscript_type": "manuscript"},
    )
    assert manuscript_response.status_code == 201
    manuscript_id = manuscript_response.json()["manuscript"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    snapshot_response = client.post(
        f"/v1/projects/{project_id}/datasets/{dataset_id}/snapshots",
        json={
            "object_uri": "object://datasets/dangling.csv",
            "input_hash_sha256": "5" * 64,
            "row_count": 12,
            "column_schema_json": {"columns": ["os_time", "os_event", "marker"]},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_id = snapshot_response.json()["snapshot"]["id"]

    template_id = client.get("/v1/templates").json()["items"][0]["id"]
    run_response = client.post(
        f"/v1/projects/{project_id}/analysis-runs",
        json={
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "params_json": {
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "marker",
            },
            "random_seed": 17,
        },
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["analysis_run"]["id"]

    artifact_response = client.post(
        f"/v1/projects/{project_id}/artifacts",
        json={
            "run_id": run_id,
            "artifact_type": "result_json",
            "storage_uri": "object://artifacts/dangling/result.json",
            "sha256": "6" * 64,
            "metadata_json": {"kind": "cox_summary"},
        },
    )
    assert artifact_response.status_code == 201
    artifact_id = artifact_response.json()["artifact"]["id"]

    bound_assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "marker associated with overall survival",
            "numeric_payload_json": {"hazard_ratio": 0.66},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "cox_summary"},
            "claim_hash": "7" * 64,
        },
    )
    assert bound_assertion_response.status_code == 201
    bound_assertion_id = bound_assertion_response.json()["assertion"]["id"]

    dangling_assertion_response = client.post(
        f"/v1/projects/{project_id}/assertions",
        json={
            "assertion_type": "result",
            "text_norm": "marker associated with disease free survival",
            "numeric_payload_json": {"hazard_ratio": 0.74},
            "source_artifact_id": artifact_id,
            "source_span_json": {"path": "cox_summary_alt"},
            "claim_hash": "8" * 64,
        },
    )
    assert dangling_assertion_response.status_code == 201
    dangling_assertion_id = dangling_assertion_response.json()["assertion"]["id"]

    verify_assertions = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"target_ids": [bound_assertion_id, dangling_assertion_id]},
    )
    assert verify_assertions.status_code == 202
    assert verify_assertions.json()["blocking_summary"] == []

    block_response = client.post(
        f"/v1/projects/{project_id}/manuscripts/{manuscript_id}/blocks",
        json={
            "section_key": "results",
            "block_order": 0,
            "block_type": "text",
            "content_md": "Marker associated with overall survival.",
            "assertion_ids": [bound_assertion_id],
        },
    )
    assert block_response.status_code == 201

    manuscript_verify = client.post(
        f"/v1/projects/{project_id}/verify",
        json={"manuscript_id": manuscript_id},
    )
    assert manuscript_verify.status_code == 202
    assert f"assertion {dangling_assertion_id} is dangling" in manuscript_verify.json()["blocking_summary"]
    binder_gate = next(
        item
        for item in manuscript_verify.json()["gate_evaluations"]
        if item["gate_name"] == "claim_evidence_binder" and item["target_kind"] == "manuscript"
    )
    assert binder_gate["status"] == "blocked"
    assert binder_gate["details_json"]["dangling_assertions"] == [dangling_assertion_id]


def test_analysis_plan_rejects_unknown_candidate_template() -> None:
    client = TestClient(create_app())

    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Template Guardrail Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["project"]["id"]

    dataset_response = client.post(
        f"/v1/projects/{project_id}/datasets/import-public",
        json={"accession": "TCGA-LUAD", "source_kind": "tcga"},
    )
    assert dataset_response.status_code == 201
    dataset_id = dataset_response.json()["dataset"]["id"]

    plan_response = client.post(
        f"/v1/projects/{project_id}/analysis/plans",
        json={
            "study_goal": "Estimate the survival association for the imported cohort",
            "dataset_ids": [dataset_id],
            "candidate_templates": ["missing.template"],
            "assumptions": [],
        },
    )
    assert plan_response.status_code == 422


def test_json_ledger_backend_persists_across_reload(tmp_path, monkeypatch) -> None:
    ledger_path = tmp_path / "ledger.json"
    monkeypatch.setenv("DROS_LEDGER_BACKEND", "json")
    monkeypatch.setenv("DROS_LEDGER_PATH", str(ledger_path))
    get_settings.cache_clear()

    client = TestClient(create_app())
    project_response = client.post(
        "/v1/projects",
        json={
            "name": "Persisted Project",
            "project_type": "public_omics",
            "compliance_level": "public",
            "owner_id": str(uuid4()),
        },
    )
    assert project_response.status_code == 201
    created_project_id = project_response.json()["project"]["id"]
    assert ledger_path.exists()

    reload_memory_store()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()

    reloaded_client = TestClient(create_app())
    list_response = reloaded_client.get("/v1/projects")
    assert list_response.status_code == 200
    items = list_response.json()["items"]["items"]
    assert [item["id"] for item in items] == [created_project_id]
