"""Transitional FK-parent sync bridge for the hybrid migration period.

During phased row-level migration, some repositories still write only to
the in-memory store while migrated repositories (e.g. ArtifactRepository)
write to Postgres.  Foreign-key constraints require parent rows to exist
in Postgres before child rows can be inserted.

This module copies parent rows from the memory store into Postgres on
demand (INSERT … if not already present).  Each ``ensure_*`` function is
**idempotent** and follows the FK dependency order so that parent rows
are created before children.

This module will be deleted once all repositories are fully migrated.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from psycopg import Connection

from .query import insert_if_not_exists, update_columns


# ------------------------------------------------------------------
# projects  (depends on: tenants ✓ seeded)
# ------------------------------------------------------------------

def ensure_project(conn: Connection, store: Any, project_id: UUID) -> None:
    project = store.projects.get(project_id)
    if project is None:
        return
    insert_if_not_exists(conn, "projects", {
        "id": project.id,
        "tenant_id": project.tenant_id,
        "name": project.name,
        "project_type": project.project_type.value,
        "status": project.status.value,
        "compliance_level": project.compliance_level.value,
        "owner_id": project.owner_id,
        "active_manuscript_id": project.active_manuscript_id,
        "created_at": project.created_at,
        "updated_at": getattr(project, "updated_at", project.created_at),
    })


# ------------------------------------------------------------------
# datasets  (depends on: tenants, projects)
# ------------------------------------------------------------------

def ensure_dataset(conn: Connection, store: Any, dataset_id: UUID) -> None:
    dataset = store.datasets.get(dataset_id)
    if dataset is None:
        return
    ensure_project(conn, store, dataset.project_id)
    insert_if_not_exists(conn, "datasets", {
        "id": dataset.id,
        "tenant_id": dataset.tenant_id,
        "project_id": dataset.project_id,
        "source_kind": dataset.source_kind.value,
        "display_name": dataset.display_name,
        "source_ref": dataset.source_ref,
        "pii_level": dataset.pii_level.value,
        "license_class": dataset.license_class.value,
        "current_snapshot_id": dataset.current_snapshot_id,
        "created_at": dataset.created_at,
        "updated_at": getattr(dataset, "updated_at", dataset.created_at),
    })


# ------------------------------------------------------------------
# dataset_snapshots  (depends on: tenants, projects, datasets)
# ------------------------------------------------------------------

def ensure_dataset_snapshot(conn: Connection, store: Any, snapshot_id: UUID) -> None:
    snapshot = store.dataset_snapshots.get(snapshot_id)
    if snapshot is None:
        return
    ensure_project(conn, store, snapshot.project_id)
    ensure_dataset(conn, store, snapshot.dataset_id)
    insert_if_not_exists(conn, "dataset_snapshots", {
        "id": snapshot.id,
        "tenant_id": snapshot.tenant_id,
        "project_id": snapshot.project_id,
        "dataset_id": snapshot.dataset_id,
        "snapshot_no": snapshot.snapshot_no,
        "object_uri": snapshot.object_uri,
        "input_hash_sha256": snapshot.input_hash_sha256,
        "row_count": snapshot.row_count,
        "column_schema_json": json.dumps(snapshot.column_schema_json, default=str),
        "deid_status": snapshot.deid_status.value,
        "phi_scan_status": snapshot.phi_scan_status.value,
        "created_at": snapshot.created_at,
    })


# ------------------------------------------------------------------
# analysis_templates  (depends on: tenants, principals ✓ seeded)
# ------------------------------------------------------------------

def ensure_analysis_template(conn: Connection, store: Any, template_id: UUID) -> None:
    template = store.analysis_templates.get(template_id)
    if template is None:
        return
    insert_if_not_exists(conn, "analysis_templates", {
        "id": template.id,
        "tenant_id": template.tenant_id,
        "code": template.code,
        "version": template.version,
        "name": template.name,
        "image_digest": template.image_digest,
        "script_hash": template.script_hash,
        "param_schema_json": json.dumps(template.param_schema_json, default=str),
        "output_schema_json": json.dumps(template.output_schema_json, default=str),
        "golden_dataset_uri": template.golden_dataset_uri,
        "expected_outputs_json": json.dumps(template.expected_outputs_json, default=str),
        "doc_template_uri": template.doc_template_uri,
        "review_status": template.review_status.value,
        "approved_by": template.approved_by,
        "approved_at": template.approved_at,
        "created_at": template.created_at,
    })


# ------------------------------------------------------------------
# workflow_instances  (depends on: tenants, projects, principals)
# ------------------------------------------------------------------

def ensure_workflow_instance(conn: Connection, store: Any, wf_id: UUID) -> None:
    wf = store.workflow_instances.get(wf_id)
    if wf is None:
        return
    ensure_project(conn, store, wf.project_id)
    if wf.parent_workflow_id is not None:
        ensure_workflow_instance(conn, store, wf.parent_workflow_id)
    insert_if_not_exists(conn, "workflow_instances", {
        "id": wf.id,
        "tenant_id": wf.tenant_id,
        "project_id": wf.project_id,
        "workflow_type": wf.workflow_type,
        "state": wf.state.value,
        "current_step": wf.current_step,
        "parent_workflow_id": wf.parent_workflow_id,
        "started_by": wf.started_by,
        "runtime_backend": wf.runtime_backend.value,
        "started_at": wf.started_at,
        "ended_at": wf.ended_at,
    })


# ------------------------------------------------------------------
# analysis_runs  (depends on: projects, dataset_snapshots,
#                  analysis_templates, workflow_instances?)
# ------------------------------------------------------------------

def ensure_analysis_run(conn: Connection, store: Any, run_id: UUID) -> None:
    run = store.analysis_runs.get(run_id)
    if run is None:
        return
    ensure_project(conn, store, run.project_id)
    ensure_dataset_snapshot(conn, store, run.snapshot_id)
    ensure_analysis_template(conn, store, run.template_id)
    if run.workflow_instance_id is not None:
        ensure_workflow_instance(conn, store, run.workflow_instance_id)
    if run.rerun_of_run_id is not None:
        ensure_analysis_run(conn, store, run.rerun_of_run_id)
    inserted = insert_if_not_exists(conn, "analysis_runs", {
        "id": run.id,
        "tenant_id": run.tenant_id,
        "project_id": run.project_id,
        "workflow_instance_id": run.workflow_instance_id,
        "snapshot_id": run.snapshot_id,
        "template_id": run.template_id,
        "state": run.state.value,
        "params_json": json.dumps(run.params_json, default=str),
        "param_hash": run.param_hash,
        "random_seed": run.random_seed,
        "container_image_digest": run.container_image_digest,
        "repro_fingerprint": run.repro_fingerprint,
        "runtime_manifest_json": json.dumps(run.runtime_manifest_json, default=str),
        "input_artifact_manifest_json": json.dumps(run.input_artifact_manifest_json, default=str),
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "exit_code": run.exit_code,
        "rerun_of_run_id": run.rerun_of_run_id,
        "job_ref": run.job_ref,
        "error_class": run.error_class,
        "error_message_trunc": run.error_message_trunc,
        "created_at": run.created_at,
    })
    if inserted:
        return
    update_columns(conn, "analysis_runs", run.id, {
        "workflow_instance_id": run.workflow_instance_id,
        "state": run.state.value,
        "params_json": json.dumps(run.params_json, default=str),
        "param_hash": run.param_hash,
        "random_seed": run.random_seed,
        "container_image_digest": run.container_image_digest,
        "repro_fingerprint": run.repro_fingerprint,
        "runtime_manifest_json": json.dumps(run.runtime_manifest_json, default=str),
        "input_artifact_manifest_json": json.dumps(run.input_artifact_manifest_json, default=str),
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "exit_code": run.exit_code,
        "rerun_of_run_id": run.rerun_of_run_id,
        "job_ref": run.job_ref,
        "error_class": run.error_class,
        "error_message_trunc": run.error_message_trunc,
    })


def ensure_project_analysis_runs(conn: Connection, store: Any, project_id: UUID) -> None:
    """Refresh all analysis runs for a project into Postgres."""
    project_runs = sorted(
        (
            run
            for run in store.analysis_runs.values()
            if run.project_id == project_id
        ),
        key=lambda run: run.created_at,
    )
    for run in project_runs:
        ensure_analysis_run(conn, store, run.id)


# ------------------------------------------------------------------
# Convenience: ensure all FK parents needed for an artifact insert
# ------------------------------------------------------------------

def ensure_artifact_parents(
    conn: Connection, store: Any, *, project_id: UUID, run_id: UUID | None
) -> None:
    """Ensure all FK parent rows needed before an artifacts INSERT."""
    ensure_project(conn, store, project_id)
    if run_id is not None:
        ensure_analysis_run(conn, store, run_id)
