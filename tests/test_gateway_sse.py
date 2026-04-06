"""Regression tests for gateway SSE fallback enrichment.

Covers: _enrich_fallback_payload must inject target_id / target_kind into
the payload dict so that front-end consumers can match fallback workflow
events to a specific workflow instance.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from backend.app.schemas.domain import AuditEventRead
from backend.app.schemas.enums import ActorType, LineageKind
from backend.app.services.gateway_service import GatewayService


def _make_audit_event(
    *,
    event_type: str = "workflow.advanced",
    target_id=None,
    target_kind: LineageKind = LineageKind.WORKFLOW_INSTANCE,
    payload_json: dict | None = None,
) -> AuditEventRead:
    return AuditEventRead(
        id=uuid4(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        actor_id=uuid4(),
        actor_type=ActorType.USER,
        event_type=event_type,
        target_kind=target_kind,
        target_id=target_id,
        request_id=None,
        trace_id=None,
        payload_json=payload_json or {},
        prev_hash=None,
        event_hash="0" * 64,
        created_at=datetime.now(UTC),
    )


def _gateway() -> GatewayService:
    """Minimal GatewayService with a stubbed repository (method is self-contained)."""
    return GatewayService(repository=None)  # type: ignore[arg-type]


# ---- enrichment regression tests ----


def test_enrich_fallback_payload_injects_target_id_for_workflow_event() -> None:
    """P2 regression: fallback SSE for workflow.* must carry target_id so
    the front-end detail page can match the event to the correct workflow."""
    wf_id = uuid4()
    event = _make_audit_event(
        event_type="workflow.advanced",
        target_id=wf_id,
        target_kind=LineageKind.WORKFLOW_INSTANCE,
    )
    result = _gateway()._enrich_fallback_payload(event)

    assert result["target_id"] == str(wf_id)
    assert result["target_kind"] == "workflow_instance"


def test_enrich_fallback_payload_injects_target_id_for_workflow_canceled() -> None:
    wf_id = uuid4()
    event = _make_audit_event(
        event_type="workflow.canceled",
        target_id=wf_id,
        target_kind=LineageKind.WORKFLOW_INSTANCE,
    )
    result = _gateway()._enrich_fallback_payload(event)

    assert result["target_id"] == str(wf_id)
    assert result["target_kind"] == "workflow_instance"


def test_enrich_fallback_payload_does_not_overwrite_existing_target_id() -> None:
    """setdefault semantics: if payload already has target_id, keep it."""
    wf_id = uuid4()
    existing_id = str(uuid4())
    event = _make_audit_event(
        target_id=wf_id,
        target_kind=LineageKind.WORKFLOW_INSTANCE,
        payload_json={"target_id": existing_id, "target_kind": "custom"},
    )
    result = _gateway()._enrich_fallback_payload(event)

    assert result["target_id"] == existing_id
    assert result["target_kind"] == "custom"


def test_enrich_fallback_payload_skips_when_no_target_id() -> None:
    event = _make_audit_event(target_id=None)
    result = _gateway()._enrich_fallback_payload(event)

    assert "target_id" not in result
    assert "target_kind" not in result


def test_fallback_structured_event_includes_enriched_payload() -> None:
    """End-to-end: _fallback_structured_event delegates to _enrich_fallback_payload
    and the resulting SSE dict has the target fields in payload."""
    wf_id = uuid4()
    event = _make_audit_event(
        event_type="workflow.advanced",
        target_id=wf_id,
        target_kind=LineageKind.WORKFLOW_INSTANCE,
    )
    sse_dict = _gateway()._fallback_structured_event(event)

    assert sse_dict["event_name"] == "workflow.advanced"
    assert sse_dict["payload"]["target_id"] == str(wf_id)
    assert sse_dict["payload"]["target_kind"] == "workflow_instance"
