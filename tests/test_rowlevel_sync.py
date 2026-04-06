from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from backend.app.db import fk_sync
from backend.app.repositories.artifact_repository import ArtifactRepository
from backend.app.schemas.domain import AnalysisRunRead
from backend.app.schemas.enums import AnalysisRunState
from backend.app.settings import get_settings


def _build_run(*, state: AnalysisRunState) -> AnalysisRunRead:
    now = datetime.now(UTC)
    return AnalysisRunRead(
        id=uuid4(),
        tenant_id=uuid4(),
        project_id=uuid4(),
        workflow_instance_id=None,
        snapshot_id=uuid4(),
        template_id=uuid4(),
        state=state,
        params_json={"time_column": "os_time"},
        param_hash="a" * 64,
        random_seed=7,
        container_image_digest="sha256:" + ("1" * 64),
        repro_fingerprint="fingerprint",
        runtime_manifest_json={"runner_status": state.value},
        input_artifact_manifest_json=[],
        started_at=now,
        finished_at=now if state == AnalysisRunState.SUCCEEDED else None,
        exit_code=0 if state == AnalysisRunState.SUCCEEDED else None,
        rerun_of_run_id=None,
        job_ref="queue://analysis-runs/example",
        error_class=None,
        error_message_trunc=None,
        created_at=now,
    )


def test_ensure_analysis_run_refreshes_existing_row(monkeypatch) -> None:
    run = _build_run(state=AnalysisRunState.SUCCEEDED)
    store = SimpleNamespace(analysis_runs={run.id: run})
    conn = object()
    update_calls: list[tuple[str, object, dict[str, object]]] = []

    monkeypatch.setattr(fk_sync, "ensure_project", lambda *args, **kwargs: None)
    monkeypatch.setattr(fk_sync, "ensure_dataset_snapshot", lambda *args, **kwargs: None)
    monkeypatch.setattr(fk_sync, "ensure_analysis_template", lambda *args, **kwargs: None)
    monkeypatch.setattr(fk_sync, "ensure_workflow_instance", lambda *args, **kwargs: None)
    monkeypatch.setattr(fk_sync, "insert_if_not_exists", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        fk_sync,
        "update_columns",
        lambda _conn, table, row_id, data: update_calls.append((table, row_id, data)),
    )

    fk_sync.ensure_analysis_run(conn, store, run.id)

    assert len(update_calls) == 1
    table, row_id, data = update_calls[0]
    assert table == "analysis_runs"
    assert row_id == run.id
    assert data["state"] == AnalysisRunState.SUCCEEDED.value
    assert data["finished_at"] == run.finished_at
    assert data["exit_code"] == 0
    assert data["job_ref"] == run.job_ref


def test_rowlevel_lineage_refreshes_project_runs_before_select(monkeypatch) -> None:
    monkeypatch.setenv("DROS_LEDGER_BACKEND", "postgres_rowlevel")
    monkeypatch.setenv("DROS_POSTGRES_DSN", "postgresql://test:test@localhost/test")
    get_settings.cache_clear()

    repo = ArtifactRepository()
    project_id = uuid4()
    refreshed: list[tuple[object, object, object]] = []

    monkeypatch.setattr(
        "backend.app.db.fk_sync.ensure_project_analysis_runs",
        lambda conn, store, pid: refreshed.append((conn, store, pid)),
    )
    monkeypatch.setattr(
        "backend.app.db.query.select_where",
        lambda *args, **kwargs: [],
    )

    uow = SimpleNamespace(conn=object())
    edges, artifacts, assertions, analysis_runs = repo.get_lineage_data(uow, project_id)

    assert refreshed == [(uow.conn, repo.store, project_id)]
    assert edges == []
    assert artifacts == []
    assert assertions == []
    assert analysis_runs == []

    get_settings.cache_clear()
