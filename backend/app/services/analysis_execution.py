from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from ..repositories.base import append_audit_event
from ..schemas.api import CreateArtifactRequest
from ..schemas.domain import AnalysisRunRead, AnalysisTemplateRead, DatasetSnapshotRead, WorkflowTaskRead
from ..schemas.enums import AnalysisRunState, ArtifactType, LineageKind, TaskState, TemplateReviewStatus, WorkflowState
from .artifact_service import ArtifactService
from .base import BaseService


class AnalysisExecutionError(RuntimeError):
    def __init__(self, *, exit_code: int, error_class: str, error_message: str) -> None:
        super().__init__(error_message)
        self.exit_code = exit_code
        self.error_class = error_class
        self.error_message = error_message


@dataclass(frozen=True, slots=True)
class RunnerArtifactSpec:
    artifact_type: ArtifactType
    storage_uri: str
    mime_type: str | None
    metadata_json: dict[str, Any]
    content_body: str

    def sha256_digest(self) -> str:
        return sha256(self.content_body.encode("utf-8")).hexdigest()

    def size_bytes(self) -> int:
        return len(self.content_body.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class RunnerExecutionOutput:
    preflight_checks: list[str]
    result_payload_json: dict[str, Any]
    artifact_specs: list[RunnerArtifactSpec]


@dataclass(slots=True)
class InMemoryJobBroker(BaseService):
    repository: object

    def queue(self, run: AnalysisRunRead) -> AnalysisRunRead:
        queued_at = self.now()
        updated = run.model_copy(
            update={
                "state": AnalysisRunState.QUEUED,
                "job_ref": f"queue://analysis-runs/{run.id}",
                "runtime_manifest_json": {
                    **run.runtime_manifest_json,
                    "job_broker": "in_memory",
                    "queued_at": queued_at.isoformat(),
                },
            }
        )
        self.repository.store.analysis_runs[run.id] = updated
        self._create_workflow_task(
            run=updated,
            task_key="analysis_run_dispatch",
            task_type="analysis_run_dispatch",
            state=TaskState.COMPLETED,
            input_payload_json={"analysis_run_id": str(run.id)},
            output_payload_json={"job_ref": updated.job_ref, "state": updated.state.value},
        )
        return updated

    def _create_workflow_task(
        self,
        *,
        run: AnalysisRunRead,
        task_key: str,
        task_type: str,
        state: TaskState,
        input_payload_json: dict[str, Any],
        output_payload_json: dict[str, Any],
    ) -> None:
        if run.workflow_instance_id is None:
            return
        now = self.now()
        task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=run.project_id,
            workflow_instance_id=run.workflow_instance_id,
            task_key=task_key,
            task_type=task_type,
            state=state,
            assignee_id=self.repository.principal_id,
            input_payload_json=input_payload_json,
            output_payload_json=output_payload_json,
            retry_count=0,
            scheduled_at=now,
            completed_at=now if state in {TaskState.COMPLETED, TaskState.BLOCKED, TaskState.FAILED} else None,
            created_at=now,
        )
        self.repository.store.workflow_tasks[task.id] = task


@dataclass(slots=True)
class DeterministicAnalysisRunner(BaseService):
    repository: object

    def start(self, run: AnalysisRunRead) -> AnalysisRunRead:
        started_at = self.now()
        updated = run.model_copy(
            update={
                "state": AnalysisRunState.RUNNING,
                "started_at": started_at,
                "runtime_manifest_json": {
                    **run.runtime_manifest_json,
                    "runner_mode": "deterministic_inline",
                    "started_at": started_at.isoformat(),
                },
            }
        )
        self.repository.store.analysis_runs[run.id] = updated
        return updated

    def execute(
        self,
        *,
        run: AnalysisRunRead,
        snapshot: DatasetSnapshotRead,
        template: AnalysisTemplateRead,
    ) -> RunnerExecutionOutput:
        preflight_checks = self._run_preflight_checks(run=run, snapshot=snapshot, template=template)
        result_payload_json = self._build_result_payload(run=run, snapshot=snapshot, template=template)
        artifact_specs = self._build_artifact_specs(
            run=run,
            snapshot=snapshot,
            template=template,
            result_payload_json=result_payload_json,
        )
        self._create_workflow_task(
            run=run,
            task_key="analysis_run_execute",
            task_type="analysis_run_execute",
            state=TaskState.COMPLETED,
            input_payload_json={
                "snapshot_id": str(snapshot.id),
                "template_id": str(template.id),
                "params_json": run.params_json,
            },
            output_payload_json={
                "state": AnalysisRunState.SUCCEEDED.value,
                "preflight_checks": preflight_checks,
                "output_artifact_types": [spec.artifact_type.value for spec in artifact_specs],
            },
        )
        return RunnerExecutionOutput(
            preflight_checks=preflight_checks,
            result_payload_json=result_payload_json,
            artifact_specs=artifact_specs,
        )

    def fail(self, *, run: AnalysisRunRead, error: AnalysisExecutionError) -> AnalysisRunRead:
        finished_at = self.now()
        updated = run.model_copy(
            update={
                "state": AnalysisRunState.FAILED,
                "finished_at": finished_at,
                "exit_code": error.exit_code,
                "error_class": error.error_class,
                "error_message_trunc": error.error_message[:512],
                "runtime_manifest_json": {
                    **run.runtime_manifest_json,
                    "runner_status": AnalysisRunState.FAILED.value,
                    "finished_at": finished_at.isoformat(),
                },
            }
        )
        self.repository.store.analysis_runs[run.id] = updated
        self._create_workflow_task(
            run=updated,
            task_key="analysis_run_execute",
            task_type="analysis_run_execute",
            state=TaskState.FAILED,
            input_payload_json={
                "snapshot_id": str(updated.snapshot_id),
                "template_id": str(updated.template_id),
                "params_json": updated.params_json,
            },
            output_payload_json={
                "state": AnalysisRunState.FAILED.value,
                "exit_code": error.exit_code,
                "error_class": error.error_class,
                "error_message_trunc": error.error_message[:512],
            },
        )
        return updated

    def succeed(
        self,
        *,
        run: AnalysisRunRead,
        output: RunnerExecutionOutput,
        emitted_artifact_ids: list[UUID],
    ) -> AnalysisRunRead:
        finished_at = self.now()
        updated = run.model_copy(
            update={
                "state": AnalysisRunState.SUCCEEDED,
                "finished_at": finished_at,
                "exit_code": 0,
                "error_class": None,
                "error_message_trunc": None,
                "runtime_manifest_json": {
                    **run.runtime_manifest_json,
                    "runner_status": AnalysisRunState.SUCCEEDED.value,
                    "finished_at": finished_at.isoformat(),
                    "preflight_checks": output.preflight_checks,
                    "output_artifact_ids": [str(artifact_id) for artifact_id in emitted_artifact_ids],
                    "output_artifact_count": len(emitted_artifact_ids),
                },
            }
        )
        self.repository.store.analysis_runs[run.id] = updated
        return updated

    def _run_preflight_checks(
        self,
        *,
        run: AnalysisRunRead,
        snapshot: DatasetSnapshotRead,
        template: AnalysisTemplateRead,
    ) -> list[str]:
        checks = ["template_approved"]
        if template.review_status != TemplateReviewStatus.APPROVED:
            raise AnalysisExecutionError(
                exit_code=64,
                error_class="TemplateApprovalError",
                error_message=f"template {template.id} is not approved",
            )

        required_params = template.param_schema_json.get("required", [])
        if isinstance(required_params, list):
            missing_params = [
                field_name
                for field_name in required_params
                if field_name not in run.params_json or run.params_json[field_name] in {None, ""}
            ]
        else:
            missing_params = []
        if missing_params:
            raise AnalysisExecutionError(
                exit_code=65,
                error_class="PreflightValidationError",
                error_message=f"missing required params: {', '.join(sorted(missing_params))}",
            )
        checks.append("required_params_present")

        available_columns = self._snapshot_columns(snapshot)
        referenced_columns = {
            str(value)
            for key, value in run.params_json.items()
            if key.endswith("_column") and isinstance(value, str) and value.strip()
        }
        missing_columns = sorted(column for column in referenced_columns if column not in available_columns)
        if missing_columns:
            raise AnalysisExecutionError(
                exit_code=66,
                error_class="PreflightValidationError",
                error_message=f"snapshot {snapshot.id} missing required columns: {', '.join(missing_columns)}",
            )
        checks.append("required_columns_present")

        if snapshot.phi_scan_status.value not in {"passed", "needs_human"}:
            raise AnalysisExecutionError(
                exit_code=67,
                error_class="PreflightValidationError",
                error_message=f"snapshot {snapshot.id} is not phi-cleared: {snapshot.phi_scan_status.value}",
            )
        checks.append("phi_scan_cleared")

        if snapshot.deid_status.value == "failed":
            raise AnalysisExecutionError(
                exit_code=68,
                error_class="PreflightValidationError",
                error_message=f"snapshot {snapshot.id} deidentification failed",
            )
        checks.append("deidentification_allowed")
        return checks

    def _build_result_payload(
        self,
        *,
        run: AnalysisRunRead,
        snapshot: DatasetSnapshotRead,
        template: AnalysisTemplateRead,
    ) -> dict[str, Any]:
        digest = sha256(
            f"{run.repro_fingerprint}:{snapshot.input_hash_sha256}:{json.dumps(run.params_json, sort_keys=True)}".encode(
                "utf-8"
            )
        ).digest()
        hazard_ratio = round(0.45 + (int.from_bytes(digest[:2], "big") % 4000) / 10000, 3)
        ci_half_width = round(0.06 + (int.from_bytes(digest[2:4], "big") % 900) / 10000, 3)
        confidence_interval = [
            round(max(0.05, hazard_ratio - ci_half_width), 3),
            round(hazard_ratio + ci_half_width, 3),
        ]
        p_value = round(0.001 + (int.from_bytes(digest[4:6], "big") % 900) / 10000, 4)
        sample_size = snapshot.row_count or 0
        return {
            "kind": "cox_summary",
            "template_id": str(template.id),
            "template_code": template.code,
            "template_version": template.version,
            "snapshot_id": str(snapshot.id),
            "repro_fingerprint": run.repro_fingerprint,
            "metrics": {
                "hazard_ratio": hazard_ratio,
                "confidence_interval": confidence_interval,
                "p_value": p_value,
                "sample_size": sample_size,
            },
            "params_json": run.params_json,
        }

    def _build_artifact_specs(
        self,
        *,
        run: AnalysisRunRead,
        snapshot: DatasetSnapshotRead,
        template: AnalysisTemplateRead,
        result_payload_json: dict[str, Any],
    ) -> list[RunnerArtifactSpec]:
        metrics = result_payload_json["metrics"]
        artifact_types = self._output_artifact_types(template)
        artifact_specs: list[RunnerArtifactSpec] = []
        for artifact_type in artifact_types:
            artifact_specs.append(
                self._build_artifact_spec(
                    artifact_type=artifact_type,
                    run=run,
                    snapshot=snapshot,
                    template=template,
                    result_payload_json=result_payload_json,
                    metrics=metrics,
                )
            )
        artifact_specs.append(
            RunnerArtifactSpec(
                artifact_type=ArtifactType.MANIFEST,
                storage_uri=f"object://analysis-runs/{run.id}/manifest.json",
                mime_type="application/json",
                metadata_json={
                    "kind": "analysis_output_manifest",
                    "analysis_run_id": str(run.id),
                    "template_code": template.code,
                    "snapshot_id": str(snapshot.id),
                    "artifact_types": [artifact_type.value for artifact_type in artifact_types],
                },
                content_body=json.dumps(
                    {
                        "analysis_run_id": str(run.id),
                        "artifact_types": [artifact_type.value for artifact_type in artifact_types],
                        "template_code": template.code,
                    },
                    sort_keys=True,
                ),
            )
        )
        artifact_specs.append(
            RunnerArtifactSpec(
                artifact_type=ArtifactType.LOG,
                storage_uri=f"object://analysis-runs/{run.id}/runner.log",
                mime_type="text/plain",
                metadata_json={
                    "kind": "runner_log",
                    "analysis_run_id": str(run.id),
                    "template_code": template.code,
                },
                content_body="\n".join(
                    [
                        f"analysis_run_id={run.id}",
                        f"template_code={template.code}",
                        f"snapshot_id={snapshot.id}",
                        "status=succeeded",
                    ]
                ),
            )
        )
        return artifact_specs

    def _build_artifact_spec(
        self,
        *,
        artifact_type: ArtifactType,
        run: AnalysisRunRead,
        snapshot: DatasetSnapshotRead,
        template: AnalysisTemplateRead,
        result_payload_json: dict[str, Any],
        metrics: dict[str, Any],
    ) -> RunnerArtifactSpec:
        if artifact_type == ArtifactType.RESULT_JSON:
            body = json.dumps(result_payload_json, sort_keys=True)
            return RunnerArtifactSpec(
                artifact_type=artifact_type,
                storage_uri=f"object://analysis-runs/{run.id}/result.json",
                mime_type="application/json",
                metadata_json=result_payload_json,
                content_body=body,
            )
        if artifact_type == ArtifactType.TABLE:
            table_payload = {
                "kind": "cox_summary_table",
                "columns": ["metric", "value"],
                "rows": [
                    {"metric": "hazard_ratio", "value": metrics["hazard_ratio"]},
                    {"metric": "confidence_interval", "value": metrics["confidence_interval"]},
                    {"metric": "p_value", "value": metrics["p_value"]},
                    {"metric": "sample_size", "value": metrics["sample_size"]},
                ],
            }
            return RunnerArtifactSpec(
                artifact_type=artifact_type,
                storage_uri=f"object://analysis-runs/{run.id}/summary-table.csv",
                mime_type="text/csv",
                metadata_json=table_payload,
                content_body="\n".join(
                    [
                        "metric,value",
                        f"hazard_ratio,{metrics['hazard_ratio']}",
                        f"confidence_interval,\"{metrics['confidence_interval']}\"",
                        f"p_value,{metrics['p_value']}",
                        f"sample_size,{metrics['sample_size']}",
                    ]
                ),
            )
        if artifact_type == ArtifactType.FIGURE:
            figure_payload = {
                "kind": "kaplan_meier_figure",
                "title": f"{template.name} result for snapshot {snapshot.snapshot_no}",
                "x_axis": run.params_json.get("time_column"),
                "y_axis": "survival_probability",
                "group_column": run.params_json.get("group_column"),
            }
            return RunnerArtifactSpec(
                artifact_type=artifact_type,
                storage_uri=f"object://analysis-runs/{run.id}/kaplan-meier.png",
                mime_type="image/png",
                metadata_json=figure_payload,
                content_body=json.dumps(figure_payload, sort_keys=True),
            )
        raise AnalysisExecutionError(
            exit_code=69,
            error_class="UnsupportedArtifactType",
            error_message=f"template requested unsupported artifact type: {artifact_type.value}",
        )

    def _output_artifact_types(self, template: AnalysisTemplateRead) -> list[ArtifactType]:
        raw_artifacts = template.expected_outputs_json.get("artifacts", [])
        artifact_types: list[ArtifactType] = []
        for raw_artifact in raw_artifacts:
            try:
                artifact_type = ArtifactType(str(raw_artifact))
            except ValueError as exc:
                raise AnalysisExecutionError(
                    exit_code=69,
                    error_class="UnsupportedArtifactType",
                    error_message=f"template requested unsupported artifact type: {raw_artifact}",
                ) from exc
            artifact_types.append(artifact_type)
        if not artifact_types:
            artifact_types.append(ArtifactType.RESULT_JSON)
        return artifact_types

    def _snapshot_columns(self, snapshot: DatasetSnapshotRead) -> set[str]:
        columns: set[str] = set()
        raw_columns = snapshot.column_schema_json.get("columns")
        if isinstance(raw_columns, list):
            columns.update(str(item).strip() for item in raw_columns if str(item).strip())
        if not columns:
            for key, value in snapshot.column_schema_json.items():
                if key == "columns":
                    continue
                if isinstance(value, dict):
                    columns.add(key)
        return columns

    def _create_workflow_task(
        self,
        *,
        run: AnalysisRunRead,
        task_key: str,
        task_type: str,
        state: TaskState,
        input_payload_json: dict[str, Any],
        output_payload_json: dict[str, Any],
    ) -> None:
        if run.workflow_instance_id is None:
            return
        now = self.now()
        task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=run.project_id,
            workflow_instance_id=run.workflow_instance_id,
            task_key=task_key,
            task_type=task_type,
            state=state,
            assignee_id=self.repository.principal_id,
            input_payload_json=input_payload_json,
            output_payload_json=output_payload_json,
            retry_count=0,
            scheduled_at=now,
            completed_at=now if state in {TaskState.COMPLETED, TaskState.BLOCKED, TaskState.FAILED} else None,
            created_at=now,
        )
        self.repository.store.workflow_tasks[task.id] = task


@dataclass(slots=True)
class InlineArtifactEmitter(BaseService):
    repository: object

    def emit(self, *, run: AnalysisRunRead, artifact_specs: list[RunnerArtifactSpec]) -> list[UUID]:
        artifact_service = ArtifactService(repository=self.repository)
        artifact_ids: list[UUID] = []
        for spec in artifact_specs:
            response = artifact_service.create_artifact(
                run.project_id,
                CreateArtifactRequest(
                    run_id=run.id,
                    artifact_type=spec.artifact_type,
                    storage_uri=spec.storage_uri,
                    mime_type=spec.mime_type,
                    sha256=spec.sha256_digest(),
                    size_bytes=spec.size_bytes(),
                    metadata_json=spec.metadata_json,
                ),
            )
            artifact_ids.append(response.artifact.id)
        self._create_workflow_task(
            run=run,
            task_key="artifact_emit",
            task_type="artifact_emit",
            state=TaskState.COMPLETED,
            input_payload_json={"analysis_run_id": str(run.id)},
            output_payload_json={"artifact_ids": [str(artifact_id) for artifact_id in artifact_ids]},
        )
        return artifact_ids

    def _create_workflow_task(
        self,
        *,
        run: AnalysisRunRead,
        task_key: str,
        task_type: str,
        state: TaskState,
        input_payload_json: dict[str, Any],
        output_payload_json: dict[str, Any],
    ) -> None:
        if run.workflow_instance_id is None:
            return
        now = self.now()
        task = WorkflowTaskRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=run.project_id,
            workflow_instance_id=run.workflow_instance_id,
            task_key=task_key,
            task_type=task_type,
            state=state,
            assignee_id=self.repository.principal_id,
            input_payload_json=input_payload_json,
            output_payload_json=output_payload_json,
            retry_count=0,
            scheduled_at=now,
            completed_at=now,
            created_at=now,
        )
        self.repository.store.workflow_tasks[task.id] = task


@dataclass(slots=True)
class InMemoryAnalysisExecutionEngine(BaseService):
    repository: object

    def execute(
        self,
        *,
        run: AnalysisRunRead,
        snapshot: DatasetSnapshotRead,
        template: AnalysisTemplateRead,
    ) -> AnalysisRunRead:
        broker = InMemoryJobBroker(repository=self.repository)
        runner = DeterministicAnalysisRunner(repository=self.repository)
        emitter = InlineArtifactEmitter(repository=self.repository)

        queued_run = broker.queue(run)
        self._update_workflow_state(queued_run, state=WorkflowState.ANALYZING, action="analysis_run_started")
        running_run = runner.start(queued_run)
        try:
            output = runner.execute(run=running_run, snapshot=snapshot, template=template)
            artifact_ids = emitter.emit(run=running_run, artifact_specs=output.artifact_specs)
            succeeded_run = runner.succeed(run=running_run, output=output, emitted_artifact_ids=artifact_ids)
        except AnalysisExecutionError as exc:
            failed_run = runner.fail(run=running_run, error=exc)
            append_audit_event(
                self.repository.store,
                project_id=failed_run.project_id,
                event_type="analysis.run.failed",
                target_kind=LineageKind.ANALYSIS_RUN,
                target_id=failed_run.id,
                payload_json={
                    "workflow_instance_id": str(failed_run.workflow_instance_id) if failed_run.workflow_instance_id else None,
                    "exit_code": exc.exit_code,
                    "error_class": exc.error_class,
                    "error_message_trunc": exc.error_message[:512],
                },
            )
            self._update_workflow_state(failed_run, state=WorkflowState.FAILED, action="analysis_run_failed")
            return failed_run

        append_audit_event(
            self.repository.store,
            project_id=succeeded_run.project_id,
            event_type="analysis.run.succeeded",
            target_kind=LineageKind.ANALYSIS_RUN,
            target_id=succeeded_run.id,
            payload_json={
                "workflow_instance_id": str(succeeded_run.workflow_instance_id) if succeeded_run.workflow_instance_id else None,
                "artifact_ids": [str(artifact_id) for artifact_id in artifact_ids],
                "output_artifact_count": len(artifact_ids),
                "finished_at": succeeded_run.finished_at.isoformat() if succeeded_run.finished_at else None,
            },
        )
        self._update_workflow_state(succeeded_run, state=WorkflowState.ANALYZED, action="analysis_run_succeeded")
        return succeeded_run

    def _update_workflow_state(self, run: AnalysisRunRead, *, state: WorkflowState, action: str) -> None:
        if run.workflow_instance_id is None:
            return
        workflow = self.repository.store.workflow_instances.get(run.workflow_instance_id)
        if workflow is None:
            return
        now = self.now()
        updated = workflow.model_copy(
            update={
                "state": state,
                "current_step": "analysis_failed" if state == WorkflowState.FAILED else "analysis_completed",
                "ended_at": now if state == WorkflowState.FAILED else None,
            }
        )
        if state == WorkflowState.ANALYZING:
            updated = workflow.model_copy(update={"state": state, "current_step": "analysis_running", "ended_at": None})
        self.repository.store.workflow_instances[workflow.id] = updated
        append_audit_event(
            self.repository.store,
            project_id=run.project_id,
            event_type="workflow.advanced",
            target_kind=LineageKind.WORKFLOW_INSTANCE,
            target_id=workflow.id,
            payload_json={"action": action, "state": updated.state.value},
        )
