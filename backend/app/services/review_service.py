from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.base import append_audit_event
from ..schemas.api import (
    CreateReviewRequest,
    CreateReviewResponse,
    DatasetPolicyCheckResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewListResponse,
    RunVerificationRequest,
    RunVerificationResponse,
    VerifyEvidenceLinkResponse,
)
from ..schemas.domain import (
    AssertionRead,
    DatasetSnapshotRead,
    GateEvaluationRead,
    ManuscriptBlockRead,
    ManuscriptRead,
    ReviewRead,
    WorkflowInstanceRead,
    WorkflowTaskRead,
)
from ..schemas.enums import (
    AssertionState,
    GateName,
    GateStatus,
    LineageKind,
    ManuscriptState,
    ReviewState,
    TaskState,
    VerifierStatus,
    WorkflowBackend,
    WorkflowState,
)
from .base import BaseService
from .evidence_control_plane import EvidenceControlPlane


@dataclass(slots=True)
class ReviewService(BaseService):
    repository: object

    def create_review(self, project_id: UUID, payload: CreateReviewRequest) -> CreateReviewResponse:
        self._require_project(project_id, "reviews:write")
        target_version_no = self._resolve_target_version_no(project_id, payload)
        review = ReviewRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            review_type=payload.review_type,
            target_kind=payload.target_kind,
            target_id=payload.target_id,
            target_version_no=target_version_no,
            state=ReviewState.PENDING,
            reviewer_id=payload.reviewer_id,
            checklist_json=payload.checklist_json,
            comments=payload.comments,
            decided_at=None,
            created_at=self.now(),
        )
        self.repository.store.reviews[review.id] = review
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="review.created",
            target_kind=LineageKind.REVIEW,
            target_id=review.id,
            payload_json={
                "review_type": review.review_type.value,
                "target_kind": review.target_kind.value,
                "target_id": str(review.target_id),
                "target_version_no": review.target_version_no,
                "reviewer_id": str(review.reviewer_id) if review.reviewer_id else None,
            },
            actor_id=self.repository.actor_id,
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="review.requested",
            target_kind=LineageKind.REVIEW,
            target_id=review.id,
            payload_json={
                "review_id": str(review.id),
                "review_type": review.review_type.value,
                "target_kind": review.target_kind.value,
                "target_id": str(review.target_id),
                "target_version_no": review.target_version_no,
                "state": review.state.value,
            },
            actor_id=self.repository.actor_id,
        )
        return CreateReviewResponse(review=review)

    def list_reviews(self, project_id: UUID, *, limit: int, offset: int) -> ReviewListResponse:
        self._require_project(project_id, "reviews:read")
        items = [
            review
            for review in self.repository.store.reviews.values()
            if review.project_id == project_id
        ]
        items.sort(key=lambda review: review.created_at, reverse=True)
        return ReviewListResponse(items=self.paginate(items, limit=limit, offset=offset))

    def decide_review(self, project_id: UUID, review_id: UUID, payload: ReviewDecisionRequest) -> ReviewDecisionResponse:
        review = self._require_review(project_id, review_id, "reviews:write")
        state_map = {
            "approve": ReviewState.APPROVED,
            "reject": ReviewState.REJECTED,
            "request_changes": ReviewState.CHANGES_REQUESTED,
        }
        next_state = state_map.get(payload.action)
        if next_state is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"unsupported review action: {payload.action}",
            )
        updated = review.model_copy(
            update={"state": next_state, "comments": payload.comments, "decided_at": self.now()}
        )
        self.repository.store.reviews[review.id] = updated
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="review.decision.recorded",
            target_kind=LineageKind.REVIEW,
            target_id=updated.id,
            payload_json={
                "action": payload.action,
                "state": updated.state.value,
                "comments": payload.comments,
                "target_kind": updated.target_kind.value,
                "target_id": str(updated.target_id),
                "target_version_no": updated.target_version_no,
            },
            actor_id=self.repository.actor_id,
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="review.completed",
            target_kind=LineageKind.REVIEW,
            target_id=updated.id,
            payload_json={
                "review_id": str(updated.id),
                "review_type": updated.review_type.value,
                "target_kind": updated.target_kind.value,
                "target_id": str(updated.target_id),
                "target_version_no": updated.target_version_no,
                "state": updated.state.value,
                "reviewer_id": str(updated.reviewer_id) if updated.reviewer_id else None,
                "decided_at": updated.decided_at.isoformat() if updated.decided_at else None,
            },
            actor_id=self.repository.actor_id,
        )
        return ReviewDecisionResponse(review=updated)

    def run_verification(self, project_id: UUID, payload: RunVerificationRequest) -> RunVerificationResponse:
        self._require_project(project_id, "reviews:write")
        now = self.now()
        control_plane = EvidenceControlPlane(repository=self.repository)
        workflow_instance_id = uuid4()
        evaluations: list[GateEvaluationRead] = []
        blocking_summary: list[str] = []
        target_ids = list(dict.fromkeys(payload.target_ids))
        manuscript: ManuscriptRead | None = None
        manuscript_blocks: list[ManuscriptBlockRead] = []

        if payload.manuscript_id is not None:
            manuscript = self._require_manuscript(project_id, payload.manuscript_id, "reviews:write")
            manuscript_blocks = self._list_current_blocks(project_id, manuscript)
            target_ids = list(
                dict.fromkeys(
                    [
                        *target_ids,
                        *[assertion_id for block in manuscript_blocks for assertion_id in block.assertion_ids],
                    ]
                )
            )

        for target_id in target_ids:
            if assertion := self.repository.store.assertions.get(target_id):
                if assertion.project_id != project_id:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"assertion {target_id} not found")
                bundle = control_plane.evaluate_assertion(
                    project_id=project_id,
                    assertion=assertion,
                    verification_id=workflow_instance_id,
                    evaluated_at=now,
                )
                self._apply_assertion_verification_state(project_id, assertion, bundle.blocking_reasons)
                evaluations.extend(bundle.evaluations)
                blocking_summary.extend(bundle.blocking_reasons)
                continue

            if artifact := self.repository.store.artifacts.get(target_id):
                if artifact.project_id != project_id:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"artifact {target_id} not found")
                evaluations.append(
                    GateEvaluationRead(
                        verification_id=workflow_instance_id,
                        gate_name=GateName.SOURCE_INTEGRITY,
                        target_kind=LineageKind.ARTIFACT,
                        target_id=target_id,
                        status=GateStatus.PASSED,
                        details_json={"target_id": str(target_id)},
                        evaluated_by=None,
                        evaluated_at=now,
                    )
                )
                continue

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"verification target {target_id} not found")

        if manuscript is not None:
            bundle = control_plane.evaluate_manuscript(
                project_id=project_id,
                manuscript=manuscript,
                blocks=manuscript_blocks,
                verification_id=workflow_instance_id,
                evaluated_at=now,
            )
            evaluations.extend(bundle.evaluations)
            blocking_summary.extend(bundle.blocking_reasons)

            if all(evaluation.status == GateStatus.PASSED for evaluation in bundle.evaluations) and manuscript.state == ManuscriptState.DRAFT:
                self.repository.store.manuscripts[manuscript.id] = manuscript.model_copy(
                    update={"state": ManuscriptState.REVIEW_REQUIRED, "updated_at": now}
                )

        blocking_summary = list(dict.fromkeys(blocking_summary))
        workflow_state = WorkflowState.BLOCKED if blocking_summary else WorkflowState.APPROVED
        verification_workflow = WorkflowInstanceRead(
            id=workflow_instance_id,
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_type="manuscript_verification",
            state=workflow_state,
            current_step=workflow_state.value,
            parent_workflow_id=None,
            started_by=self.repository.principal_id,
            runtime_backend=WorkflowBackend.QUEUE_WORKERS,
            started_at=now,
            ended_at=now,
        )
        self.repository.store.workflow_instances[verification_workflow.id] = verification_workflow
        verification_task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_instance_id=workflow_instance_id,
            task_key="verify",
            task_type="verification",
            state=TaskState.BLOCKED if blocking_summary else TaskState.COMPLETED,
            assignee_id=self.repository.principal_id,
            input_payload_json=payload.model_dump(mode="json"),
            output_payload_json={
                "blocking_summary": blocking_summary,
                "gate_count": len(evaluations),
            },
            retry_count=0,
            scheduled_at=now,
            completed_at=now,
            created_at=now,
        )
        self.repository.store.workflow_tasks[verification_task.id] = verification_task
        response = RunVerificationResponse(
            workflow_instance_id=workflow_instance_id,
            gate_evaluations=evaluations,
            verifier_result=None,
            blocking_summary=blocking_summary,
        )
        self.repository.store.verification_runs[workflow_instance_id] = response
        if manuscript is not None:
            self.repository.store.manuscript_verifications[(manuscript.id, manuscript.current_version_no)] = response
        self._append_gate_audit_events(project_id, evaluations)
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="verification.completed",
            target_kind=LineageKind.MANUSCRIPT if manuscript is not None else LineageKind.PROJECT,
            target_id=manuscript.id if manuscript is not None else project_id,
            payload_json={
                "manuscript_id": str(manuscript.id) if manuscript is not None else None,
                "version_no": manuscript.current_version_no if manuscript is not None else None,
                "target_ids": [str(target_id) for target_id in target_ids],
                "blocking_summary": blocking_summary,
                "gate_evaluations": [
                    {
                        "gate_name": evaluation.gate_name.value,
                        "target_kind": evaluation.target_kind.value,
                        "target_id": str(evaluation.target_id),
                        "status": evaluation.status.value,
                    }
                    for evaluation in evaluations
                ],
            },
        )
        return response

    def run_dataset_policy_checks(self, project_id: UUID, dataset_id: UUID) -> DatasetPolicyCheckResponse:
        dataset = self.repository.require_project_scoped(
            "datasets",
            project_id,
            dataset_id,
            "dataset",
            required_scopes=("datasets:read",),
        )
        snapshot = (
            self.repository.store.dataset_snapshots.get(dataset.current_snapshot_id)
            if dataset.current_snapshot_id
            else None
        )
        if snapshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"dataset {dataset_id} has no snapshot")
        blocking_reasons = self._dataset_policy_blocking_reasons(snapshot)
        allowed = not blocking_reasons
        if blocking_reasons:
            self._append_dataset_snapshot_blocked_event(
                project_id=project_id,
                dataset_id=dataset.id,
                snapshot=snapshot,
                blocking_reasons=blocking_reasons,
            )
        return DatasetPolicyCheckResponse(
            snapshot_id=snapshot.id,
            phi_scan_status=snapshot.phi_scan_status.value,
            deid_status=snapshot.deid_status.value,
            blocking_reasons=blocking_reasons,
            allowed=allowed,
        )

    def verify_evidence_link(self, project_id: UUID, link_id: UUID) -> VerifyEvidenceLinkResponse:
        link = self.repository.require_project_scoped(
            "evidence_links",
            project_id,
            link_id,
            "evidence link",
            required_scopes=("reviews:write",),
        )
        reasons = EvidenceControlPlane(repository=self.repository).evaluate_evidence_link(link=link)
        updated = link.model_copy(
            update={
                "verifier_status": VerifierStatus.BLOCKED if reasons else VerifierStatus.PASSED,
                "confidence": link.confidence if link.confidence is not None else (0.0 if reasons else 1.0),
            }
        )
        self.repository.store.evidence_links[link.id] = updated
        evidence_source = self.repository.store.evidence_sources.get(updated.evidence_source_id)
        candidate_identifier = evidence_source.external_id_norm if evidence_source is not None else None
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="evidence.blocked" if reasons else "evidence.linked",
            target_kind=LineageKind.ASSERTION,
            target_id=updated.assertion_id,
            payload_json={
                "assertion_id": str(updated.assertion_id),
                "evidence_link_id": str(link_id),
                "evidence_source_id": str(updated.evidence_source_id),
                "candidate_identifier": candidate_identifier,
                "relation_type": updated.relation_type.value,
                "verifier_status": updated.verifier_status.value,
                "reason": "; ".join(reasons) if reasons else None,
                "needs_human_items": reasons,
                "reasons": reasons,
            },
            actor_id=self.repository.actor_id,
        )
        return VerifyEvidenceLinkResponse(evidence_link=updated)

    def _require_project(self, project_id: UUID, *required_scopes: str) -> None:
        self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_manuscript(self, project_id: UUID, manuscript_id: UUID, *required_scopes: str) -> ManuscriptRead:
        return self.repository.require_project_scoped(
            "manuscripts",
            project_id,
            manuscript_id,
            "manuscript",
            required_scopes=tuple(required_scopes),
        )

    def _require_review(self, project_id: UUID, review_id: UUID, *required_scopes: str) -> ReviewRead:
        return self.repository.require_project_scoped(
            "reviews",
            project_id,
            review_id,
            "review",
            required_scopes=tuple(required_scopes),
        )

    def _dataset_policy_blocking_reasons(self, snapshot: DatasetSnapshotRead) -> list[str]:
        blocking_reasons: list[str] = []
        if snapshot.phi_scan_status.value == "pending":
            blocking_reasons.append("phi_scan_pending")
        elif snapshot.phi_scan_status.value == "blocked":
            blocking_reasons.append("phi_scan_blocked")

        if snapshot.deid_status.value == "pending":
            blocking_reasons.append("deidentification_pending")
        elif snapshot.deid_status.value == "failed":
            blocking_reasons.append("deidentification_failed")
        return blocking_reasons

    def _append_dataset_snapshot_blocked_event(
        self,
        *,
        project_id: UUID,
        dataset_id: UUID,
        snapshot: DatasetSnapshotRead,
        blocking_reasons: list[str],
    ) -> None:
        reason = "; ".join(blocking_reasons)
        for event in self.repository.store.audit_events.values():
            if (
                event.project_id == project_id
                and event.event_type == "dataset.snapshot.blocked"
                and event.target_id == snapshot.id
                and (event.payload_json or {}).get("reason") == reason
                and (event.payload_json or {}).get("blocked_checks") == blocking_reasons
            ):
                return

        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="dataset.snapshot.blocked",
            target_kind=LineageKind.DATASET_SNAPSHOT,
            target_id=snapshot.id,
            payload_json={
                "dataset_id": str(dataset_id),
                "snapshot_id": str(snapshot.id),
                "blocked_checks": blocking_reasons,
                "reason": reason,
            },
            actor_id=self.repository.actor_id,
        )

    def _resolve_target_version_no(self, project_id: UUID, payload: CreateReviewRequest) -> int | None:
        if payload.target_kind != LineageKind.MANUSCRIPT:
            if payload.target_version_no is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="target_version_no is only supported for manuscript reviews",
                )
            return None

        manuscript = self._require_manuscript(project_id, payload.target_id, "reviews:write")
        target_version_no = payload.target_version_no or manuscript.current_version_no
        if target_version_no > manuscript.current_version_no:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"target_version_no {target_version_no} is ahead of manuscript current_version_no "
                    f"{manuscript.current_version_no}"
                ),
            )
        return target_version_no

    def _list_current_blocks(self, project_id: UUID, manuscript: ManuscriptRead) -> list[ManuscriptBlockRead]:
        blocks = [
            block
            for block in self.repository.store.manuscript_blocks.values()
            if block.project_id == project_id
            and block.manuscript_id == manuscript.id
            and block.version_no == manuscript.current_version_no
        ]
        blocks.sort(key=lambda block: (block.section_key.value, block.block_order))
        return blocks

    def _apply_assertion_verification_state(
        self,
        project_id: UUID,
        assertion: AssertionRead,
        reasons: list[str],
    ) -> None:
        next_state = AssertionState.BLOCKED if reasons else AssertionState.VERIFIED
        previous_state = assertion.state
        updated_assertion = assertion.model_copy(update={"state": next_state})
        self.repository.store.assertions[assertion.id] = updated_assertion
        if previous_state != next_state:
            append_audit_event(
                self.repository.store,
                project_id=project_id,
                event_type=f"assertion.{next_state.value}",
                target_kind=LineageKind.ASSERTION,
                target_id=assertion.id,
                payload_json={
                    "previous_state": previous_state.value,
                    "state": next_state.value,
                    "reasons": reasons,
                },
            )

    def _append_gate_audit_events(self, project_id: UUID, evaluations: list[GateEvaluationRead]) -> None:
        for evaluation in evaluations:
            append_audit_event(
                self.repository.store,
                project_id=project_id,
                event_type="evidence_control_plane.gate_evaluated",
                target_kind=evaluation.target_kind,
                target_id=evaluation.target_id,
                payload_json={
                    "verification_id": str(evaluation.verification_id) if evaluation.verification_id else None,
                    "gate_name": evaluation.gate_name.value,
                    "status": evaluation.status.value,
                    "details_json": evaluation.details_json,
                },
            )
