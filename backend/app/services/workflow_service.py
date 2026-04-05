from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.base import append_audit_event
from ..schemas.agents import AnalysisAgentResult
from ..schemas.api import (
    AdvanceWorkflowRequest,
    AnalysisRunDetailResponse,
    AnalysisRunListResponse,
    CancelWorkflowRequest,
    CreateAnalysisPlanRequest,
    CreateAnalysisPlanResponse,
    CreateAnalysisRunRequest,
    CreateAnalysisRunResponse,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    WorkflowDetailResponse,
    WorkflowListResponse,
)
from ..schemas.domain import AnalysisRunRead, LineageEdgeRead, WorkflowInstanceRead, WorkflowTaskRead
from ..schemas.enums import (
    AnalysisRunState,
    LineageEdgeType,
    LineageKind,
    TaskState,
    WorkflowBackend,
    WorkflowState,
)
from .analysis_execution import InMemoryAnalysisExecutionEngine
from .base import BaseService


TERMINAL_WORKFLOW_STATES = {
    WorkflowState.APPROVED,
    WorkflowState.BLOCKED,
    WorkflowState.EXPORTED,
    WorkflowState.FAILED,
}

DEFAULT_WORKFLOW_SEQUENCE = {
    WorkflowState.CREATED: WorkflowState.RETRIEVING,
    WorkflowState.RETRIEVING: WorkflowState.RETRIEVED,
    WorkflowState.RETRIEVED: WorkflowState.STRUCTURING,
    WorkflowState.STRUCTURING: WorkflowState.STRUCTURED,
    WorkflowState.STRUCTURED: WorkflowState.ANALYZING,
    WorkflowState.ANALYZING: WorkflowState.ANALYZED,
    WorkflowState.ANALYZED: WorkflowState.ASSERTING,
    WorkflowState.ASSERTING: WorkflowState.ASSERTED,
    WorkflowState.ASSERTED: WorkflowState.WRITING,
    WorkflowState.WRITING: WorkflowState.VERIFYING,
    WorkflowState.VERIFYING: WorkflowState.APPROVED,
}

ACTION_TRANSITIONS = {
    "block": {state: WorkflowState.BLOCKED for state in WorkflowState if state not in TERMINAL_WORKFLOW_STATES},
    "needs_human": {state: WorkflowState.NEEDS_HUMAN for state in WorkflowState if state not in TERMINAL_WORKFLOW_STATES},
    "verify": {
        WorkflowState.ASSERTED: WorkflowState.VERIFYING,
        WorkflowState.WRITING: WorkflowState.VERIFYING,
        WorkflowState.NEEDS_HUMAN: WorkflowState.VERIFYING,
    },
    "approve": {
        WorkflowState.VERIFYING: WorkflowState.APPROVED,
        WorkflowState.NEEDS_HUMAN: WorkflowState.APPROVED,
    },
    "export": {
        WorkflowState.APPROVED: WorkflowState.EXPORTED,
    },
}


@dataclass(slots=True)
class WorkflowService(BaseService):
    repository: object

    def create_analysis_plan(self, project_id: UUID, payload: CreateAnalysisPlanRequest) -> CreateAnalysisPlanResponse:
        self._require_project(project_id, "workflows:write")
        for dataset_id in payload.dataset_ids:
            self._require_dataset(project_id, dataset_id, "workflows:write")

        template = self._pick_template(payload.candidate_templates)
        now = self.now()
        workflow = WorkflowInstanceRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_type="analysis_planning",
            state=WorkflowState.ANALYZED,
            current_step="plan_ready",
            parent_workflow_id=None,
            started_by=self.repository.principal_id,
            runtime_backend=WorkflowBackend.QUEUE_WORKERS,
            started_at=now,
            ended_at=now,
        )
        self.repository.store.workflow_instances[workflow.id] = workflow
        task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_instance_id=workflow.id,
            task_key="analysis_plan",
            task_type="analysis_plan",
            state=TaskState.COMPLETED,
            assignee_id=self.repository.principal_id,
            input_payload_json=payload.model_dump(),
            output_payload_json={"template_id": str(template.id)},
            retry_count=0,
            scheduled_at=now,
            completed_at=now,
            created_at=now,
        )
        self.repository.store.workflow_tasks[task.id] = task
        plan = AnalysisAgentResult(
            template_id=str(template.id),
            template_version=template.version,
            parameter_json={
                "time_column": "os_time",
                "event_column": "os_event",
                "group_column": "risk_group",
                "covariates": ["age", "stage"],
            },
            preflight_checks=[
                "snapshot_exists",
                "template_whitelisted",
                "required_columns_expected",
            ],
            rationale=[
                payload.study_goal,
                f"matched template code {template.code}",
            ],
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="analysis.plan.created",
            target_kind=LineageKind.WORKFLOW_INSTANCE,
            target_id=workflow.id,
            payload_json={"dataset_ids": [str(dataset_id) for dataset_id in payload.dataset_ids]},
        )
        return CreateAnalysisPlanResponse(workflow_instance_id=workflow.id, plan=plan)

    def create_workflow(self, project_id: UUID, payload: CreateWorkflowRequest) -> CreateWorkflowResponse:
        self._require_project(project_id, "workflows:write")
        now = self.now()
        workflow = WorkflowInstanceRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_type=payload.workflow_type,
            state=WorkflowState.CREATED,
            current_step="created",
            parent_workflow_id=payload.parent_workflow_id,
            started_by=payload.started_by or self.repository.principal_id,
            runtime_backend=payload.runtime_backend,
            started_at=now,
            ended_at=None,
        )
        self.repository.store.workflow_instances[workflow.id] = workflow
        task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_instance_id=workflow.id,
            task_key="start",
            task_type=payload.workflow_type,
            state=TaskState.PENDING,
            assignee_id=workflow.started_by,
            input_payload_json=payload.model_dump(),
            output_payload_json={},
            retry_count=0,
            scheduled_at=now,
            completed_at=None,
            created_at=now,
        )
        self.repository.store.workflow_tasks[task.id] = task
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="workflow.started",
            target_kind=LineageKind.WORKFLOW_INSTANCE,
            target_id=workflow.id,
            payload_json={"workflow_type": payload.workflow_type},
            actor_id=self.repository.actor_id,
        )
        return CreateWorkflowResponse(workflow=workflow)

    def list_workflows(self, project_id: UUID, *, limit: int, offset: int) -> WorkflowListResponse:
        self._require_project(project_id, "workflows:read")
        workflows = sorted(
            [
                workflow
                for workflow in self.repository.store.workflow_instances.values()
                if workflow.project_id == project_id
            ],
            key=lambda workflow: workflow.started_at,
            reverse=True,
        )
        return WorkflowListResponse(items=self.paginate(workflows, limit=limit, offset=offset))

    def get_workflow(self, project_id: UUID, workflow_instance_id: UUID) -> WorkflowDetailResponse:
        workflow = self._require_workflow(project_id, workflow_instance_id, "workflows:read")
        tasks = [
            task
            for task in self.repository.store.workflow_tasks.values()
            if task.workflow_instance_id == workflow_instance_id
        ]
        tasks.sort(key=lambda task: task.created_at)
        verification = self.repository.store.verification_runs.get(workflow_instance_id)
        gate_evaluations = verification.gate_evaluations if verification is not None else []
        return WorkflowDetailResponse(workflow=workflow, tasks=tasks, gate_evaluations=gate_evaluations)

    def advance_workflow(
        self,
        project_id: UUID,
        workflow_instance_id: UUID,
        payload: AdvanceWorkflowRequest,
    ) -> WorkflowDetailResponse:
        workflow = self._require_workflow(project_id, workflow_instance_id, "workflows:write")
        next_state = self._resolve_next_state(workflow.state, payload.action)
        now = self.now()
        updated = workflow.model_copy(
            update={
                "state": next_state,
                "current_step": next_state.value,
                "ended_at": now if next_state in TERMINAL_WORKFLOW_STATES else None,
            }
        )
        self.repository.store.workflow_instances[workflow.id] = updated

        if payload.task_id:
            task = self.repository.store.workflow_tasks.get(payload.task_id)
            if task and task.workflow_instance_id == workflow_instance_id:
                task_state = TaskState.COMPLETED if next_state not in {WorkflowState.BLOCKED, WorkflowState.NEEDS_HUMAN, WorkflowState.FAILED} else TaskState.BLOCKED
                self.repository.store.workflow_tasks[task.id] = task.model_copy(
                    update={
                        "state": task_state,
                        "output_payload_json": {
                            "action": payload.action,
                            "comments": payload.comments,
                            "state": next_state.value,
                        },
                        "completed_at": now,
                    }
                )

        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="workflow.advanced",
            target_kind=LineageKind.WORKFLOW_INSTANCE,
            target_id=workflow.id,
            payload_json={"action": payload.action, "state": next_state.value},
        )
        return self.get_workflow(project_id, workflow_instance_id)

    def cancel_workflow(
        self,
        project_id: UUID,
        workflow_instance_id: UUID,
        payload: CancelWorkflowRequest,
    ) -> WorkflowDetailResponse:
        workflow = self._require_workflow(project_id, workflow_instance_id, "workflows:write")
        updated = workflow.model_copy(
            update={"state": WorkflowState.FAILED, "current_step": "canceled", "ended_at": self.now()}
        )
        self.repository.store.workflow_instances[workflow.id] = updated
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="workflow.canceled",
            target_kind=LineageKind.WORKFLOW_INSTANCE,
            target_id=workflow.id,
            payload_json={"reason": payload.reason, "requested_by": str(payload.requested_by) if payload.requested_by else None},
            actor_id=self.repository.actor_id,
        )
        return self.get_workflow(project_id, workflow_instance_id)

    def create_analysis_run(self, project_id: UUID, payload: CreateAnalysisRunRequest) -> CreateAnalysisRunResponse:
        self._require_project(project_id, "workflows:write")
        snapshot = self._require_snapshot(project_id, payload.snapshot_id, "workflows:write")
        template = self.repository.store.analysis_templates.get(payload.template_id)
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"template {payload.template_id} not found")
        if payload.workflow_instance_id is not None:
            self._require_workflow(project_id, payload.workflow_instance_id, "workflows:write")

        params_blob = json.dumps(payload.params_json, sort_keys=True).encode("utf-8")
        param_hash = sha256(params_blob).hexdigest()
        repro_fingerprint = sha256(
            f"{snapshot.id}:{template.id}:{param_hash}:{payload.random_seed}".encode("utf-8")
        ).hexdigest()
        run = AnalysisRunRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            workflow_instance_id=payload.workflow_instance_id,
            snapshot_id=payload.snapshot_id,
            template_id=payload.template_id,
            state=AnalysisRunState.REQUESTED,
            params_json=payload.params_json,
            param_hash=param_hash,
            random_seed=payload.random_seed,
            container_image_digest=template.image_digest,
            repro_fingerprint=repro_fingerprint,
            runtime_manifest_json={
                "mode": "in_memory",
                "job_broker": "in_memory",
                "runner_mode": "deterministic_inline",
                "artifact_emitter": "inline",
                "template_code": template.code,
                "template_version": template.version,
            },
            input_artifact_manifest_json=[
                {
                    "dataset_snapshot_id": str(snapshot.id),
                    "object_uri": snapshot.object_uri,
                    "input_hash_sha256": snapshot.input_hash_sha256,
                }
            ],
            started_at=None,
            finished_at=None,
            exit_code=None,
            rerun_of_run_id=None,
            job_ref=None,
            error_class=None,
            error_message_trunc=None,
            created_at=self.now(),
        )
        self.repository.store.analysis_runs[run.id] = run
        edge = LineageEdgeRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            from_kind=LineageKind.DATASET_SNAPSHOT,
            from_id=snapshot.id,
            edge_type=LineageEdgeType.INPUT_OF,
            to_kind=LineageKind.ANALYSIS_RUN,
            to_id=run.id,
            created_at=self.now(),
        )
        self.repository.store.lineage_edges[edge.id] = edge
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="analysis.run.requested",
            target_kind=LineageKind.ANALYSIS_RUN,
            target_id=run.id,
            payload_json={
                "snapshot_id": str(payload.snapshot_id),
                "template_id": str(payload.template_id),
                "workflow_instance_id": str(payload.workflow_instance_id) if payload.workflow_instance_id else None,
                "repro_fingerprint": repro_fingerprint,
            },
        )
        executed_run = InMemoryAnalysisExecutionEngine(repository=self.repository).execute(
            run=run,
            snapshot=snapshot,
            template=template,
        )
        return CreateAnalysisRunResponse(analysis_run=executed_run)

    def list_analysis_runs(self, project_id: UUID, *, limit: int, offset: int) -> AnalysisRunListResponse:
        self._require_project(project_id, "workflows:read")
        runs = sorted(
            [
                run
                for run in self.repository.store.analysis_runs.values()
                if run.project_id == project_id
            ],
            key=lambda run: run.created_at,
            reverse=True,
        )
        return AnalysisRunListResponse(items=self.paginate(runs, limit=limit, offset=offset))

    def get_analysis_run(self, project_id: UUID, run_id: UUID) -> AnalysisRunDetailResponse:
        run = self._require_analysis_run(project_id, run_id, "workflows:read")
        artifacts = [
            artifact
            for artifact in self.repository.store.artifacts.values()
            if artifact.project_id == project_id and artifact.run_id == run_id
        ]
        artifacts.sort(key=lambda artifact: artifact.created_at)
        return AnalysisRunDetailResponse(analysis_run=run, artifacts=artifacts)

    def _resolve_next_state(self, current: WorkflowState, action: str | None) -> WorkflowState:
        if action is not None:
            transition = ACTION_TRANSITIONS.get(action, {}).get(current)
            if transition is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"workflow action {action} is not allowed from state {current.value}",
                )
            return transition
        transition = DEFAULT_WORKFLOW_SEQUENCE.get(current)
        if transition is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"workflow cannot advance from terminal state {current.value}",
            )
        return transition

    def _pick_template(self, candidate_templates: list[str]) -> object:
        templates = list(self.repository.store.analysis_templates.values())
        if candidate_templates:
            wanted = {candidate.strip() for candidate in candidate_templates}
            matches = [
                template
                for template in templates
                if str(template.id) in wanted or template.code in wanted
            ]
            if not matches:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"no approved template matched candidate_templates: {sorted(wanted)}",
                )
            if len(matches) > 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="multiple templates matched candidate_templates; narrow the request",
                )
            return matches[0]
        if len(templates) != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="multiple templates are available; candidate_templates must be specified",
            )
        return templates[0]

    def _require_project(self, project_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_dataset(self, project_id: UUID, dataset_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project_scoped(
            "datasets",
            project_id,
            dataset_id,
            "dataset",
            required_scopes=tuple(required_scopes),
        )

    def _require_snapshot(self, project_id: UUID, snapshot_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project_scoped(
            "dataset_snapshots",
            project_id,
            snapshot_id,
            "snapshot",
            required_scopes=tuple(required_scopes),
        )

    def _require_workflow(self, project_id: UUID, workflow_instance_id: UUID, *required_scopes: str) -> WorkflowInstanceRead:
        return self.repository.require_project_scoped(
            "workflow_instances",
            project_id,
            workflow_instance_id,
            "workflow",
            required_scopes=tuple(required_scopes),
        )

    def _require_analysis_run(self, project_id: UUID, run_id: UUID, *required_scopes: str) -> AnalysisRunRead:
        return self.repository.require_project_scoped(
            "analysis_runs",
            project_id,
            run_id,
            "analysis run",
            required_scopes=tuple(required_scopes),
        )
