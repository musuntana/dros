from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, MutableMapping
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from ..auth import DEFAULT_PRINCIPAL_ID, DEFAULT_TENANT_ID, ROLE_SCOPE_TOKENS, current_auth_context
from ..schemas.api import RunVerificationResponse
from ..schemas.domain import (
    AnalysisRunRead,
    AnalysisTemplateRead,
    ArtifactRead,
    AssertionRead,
    AuditEventRead,
    BlockAssertionLinkRead,
    DatasetRead,
    DatasetSnapshotRead,
    EvidenceChunkRead,
    EvidenceLinkRead,
    EvidenceSourceRead,
    ExportJobRead,
    LineageEdgeRead,
    ManuscriptBlockRead,
    ManuscriptRead,
    ProjectMemberRead,
    ProjectRead,
    ReviewRead,
    WorkflowInstanceRead,
    WorkflowTaskRead,
)
from ..schemas.enums import (
    ActorType,
    ComplianceLevel,
    LineageKind,
    ProjectRole,
    TemplateReviewStatus,
)
from ..settings import get_settings
DEFAULT_TEMPLATE_ID = UUID("00000000-0000-0000-0000-000000000101")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class InMemoryLedger:
    projects: dict[UUID, Any] = field(default_factory=dict)
    project_members: dict[tuple[UUID, UUID], Any] = field(default_factory=dict)
    datasets: dict[UUID, Any] = field(default_factory=dict)
    dataset_snapshots: dict[UUID, Any] = field(default_factory=dict)
    snapshot_numbers: dict[UUID, int] = field(default_factory=dict)
    analysis_templates: dict[UUID, AnalysisTemplateRead] = field(default_factory=dict)
    workflow_instances: dict[UUID, Any] = field(default_factory=dict)
    workflow_tasks: dict[UUID, Any] = field(default_factory=dict)
    analysis_runs: dict[UUID, Any] = field(default_factory=dict)
    artifacts: dict[UUID, Any] = field(default_factory=dict)
    lineage_edges: dict[UUID, Any] = field(default_factory=dict)
    assertions: dict[UUID, Any] = field(default_factory=dict)
    evidence_sources: dict[UUID, Any] = field(default_factory=dict)
    evidence_chunks: dict[UUID, Any] = field(default_factory=dict)
    evidence_links: dict[UUID, Any] = field(default_factory=dict)
    project_evidence_bindings: dict[tuple[UUID, UUID], datetime] = field(default_factory=dict)
    ncbi_search_cache: dict[str, Any] = field(default_factory=dict)
    ncbi_resolve_cache: dict[str, Any] = field(default_factory=dict)
    manuscripts: dict[UUID, Any] = field(default_factory=dict)
    manuscript_blocks: dict[UUID, Any] = field(default_factory=dict)
    block_assertion_links: dict[tuple[UUID, UUID], Any] = field(default_factory=dict)
    verification_runs: dict[UUID, Any] = field(default_factory=dict)
    manuscript_verifications: dict[tuple[UUID, int], Any] = field(default_factory=dict)
    reviews: dict[UUID, Any] = field(default_factory=dict)
    export_jobs: dict[UUID, Any] = field(default_factory=dict)
    audit_events: dict[UUID, AuditEventRead] = field(default_factory=dict)


class PersistentDict(MutableMapping[Any, Any]):
    def __init__(self, initial: dict[Any, Any], on_change) -> None:
        self._data = dict(initial)
        self._on_change = on_change

    def __getitem__(self, key: Any) -> Any:
        return self._data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._data[key] = value
        self._on_change()

    def __delitem__(self, key: Any) -> None:
        del self._data[key]
        self._on_change()

    def __iter__(self) -> Iterator[Any]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        if self._data:
            self._data.clear()
            self._on_change()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._data.update(*args, **kwargs)
        self._on_change()

    def pop(self, key: Any, default: Any = ... ) -> Any:
        if default is ...:
            value = self._data.pop(key)
        else:
            value = self._data.pop(key, default)
        self._on_change()
        return value

    def unwrap(self) -> dict[Any, Any]:
        return dict(self._data)

    def __repr__(self) -> str:
        return repr(self._data)


@dataclass(frozen=True, slots=True)
class StoreCodec:
    key_encoder: Any
    key_decoder: Any
    value_encoder: Any
    value_decoder: Any


def _encode_uuid(value: UUID) -> str:
    return str(value)


def _decode_uuid(value: str) -> UUID:
    return UUID(value)


def _encode_uuid_pair(value: tuple[UUID, UUID]) -> list[str]:
    return [str(value[0]), str(value[1])]


def _decode_uuid_pair(value: Iterable[str]) -> tuple[UUID, UUID]:
    left, right = list(value)
    return UUID(left), UUID(right)


def _encode_uuid_int_pair(value: tuple[UUID, int]) -> list[str | int]:
    return [str(value[0]), value[1]]


def _decode_uuid_int_pair(value: Iterable[str | int]) -> tuple[UUID, int]:
    left, right = list(value)
    return UUID(str(left)), int(right)


def _encode_model(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json")


def _decode_model(model: type, payload: dict[str, Any]) -> Any:
    return model.model_validate(payload)


def _encode_datetime(value: datetime) -> str:
    return value.isoformat()


def _decode_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _identity(value: Any) -> Any:
    return value


STORE_CODECS: dict[str, StoreCodec] = {
    "projects": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(ProjectRead, value)),
    "project_members": StoreCodec(_encode_uuid_pair, _decode_uuid_pair, _encode_model, lambda value: _decode_model(ProjectMemberRead, value)),
    "datasets": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(DatasetRead, value)),
    "dataset_snapshots": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(DatasetSnapshotRead, value)),
    "snapshot_numbers": StoreCodec(_encode_uuid, _decode_uuid, _identity, int),
    "analysis_templates": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(AnalysisTemplateRead, value)),
    "workflow_instances": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(WorkflowInstanceRead, value)),
    "workflow_tasks": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(WorkflowTaskRead, value)),
    "analysis_runs": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(AnalysisRunRead, value)),
    "artifacts": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(ArtifactRead, value)),
    "lineage_edges": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(LineageEdgeRead, value)),
    "assertions": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(AssertionRead, value)),
    "evidence_sources": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(EvidenceSourceRead, value)),
    "evidence_chunks": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(EvidenceChunkRead, value)),
    "evidence_links": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(EvidenceLinkRead, value)),
    "project_evidence_bindings": StoreCodec(_encode_uuid_pair, _decode_uuid_pair, _encode_datetime, _decode_datetime),
    "ncbi_search_cache": StoreCodec(_identity, _identity, _identity, _identity),
    "ncbi_resolve_cache": StoreCodec(_identity, _identity, _identity, _identity),
    "manuscripts": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(ManuscriptRead, value)),
    "manuscript_blocks": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(ManuscriptBlockRead, value)),
    "block_assertion_links": StoreCodec(_encode_uuid_pair, _decode_uuid_pair, _encode_model, lambda value: _decode_model(BlockAssertionLinkRead, value)),
    "verification_runs": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(RunVerificationResponse, value)),
    "manuscript_verifications": StoreCodec(_encode_uuid_int_pair, _decode_uuid_int_pair, _encode_model, lambda value: _decode_model(RunVerificationResponse, value)),
    "reviews": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(ReviewRead, value)),
    "export_jobs": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(ExportJobRead, value)),
    "audit_events": StoreCodec(_encode_uuid, _decode_uuid, _encode_model, lambda value: _decode_model(AuditEventRead, value)),
}


def seed_templates(store: InMemoryLedger) -> None:
    if store.analysis_templates:
        return

    now = utcnow()
    store.analysis_templates[DEFAULT_TEMPLATE_ID] = AnalysisTemplateRead(
        id=DEFAULT_TEMPLATE_ID,
        tenant_id=None,
        code="survival.cox.v1",
        version="1.0.3",
        name="Standard Cox Survival Analysis",
        image_digest="sha256:template-runner-survival-cox-v1",
        script_hash="a" * 64,
        param_schema_json={
            "type": "object",
            "required": ["time_column", "event_column", "group_column"],
            "properties": {
                "time_column": {"type": "string"},
                "event_column": {"type": "string"},
                "group_column": {"type": "string"},
                "covariates": {"type": "array", "items": {"type": "string"}},
            },
        },
        output_schema_json={
            "type": "object",
            "properties": {
                "hazard_ratio": {"type": "number"},
                "confidence_interval": {"type": "array", "items": {"type": "number"}},
                "p_value": {"type": "number"},
            },
        },
        golden_dataset_uri="object://golden/survival-cox-v1.csv",
        expected_outputs_json={"artifacts": ["result_json", "table", "figure"]},
        doc_template_uri="object://templates/survival-cox-v1.qmd",
        review_status=TemplateReviewStatus.APPROVED,
        approved_by=DEFAULT_PRINCIPAL_ID,
        approved_at=now,
        created_at=now,
    )


class LedgerProvider:
    _POSTGRES_SNAPSHOT_KEY = "default"

    def __init__(self) -> None:
        self._store: InMemoryLedger | None = None
        self._persisting = False

    def get_store(self) -> InMemoryLedger:
        if self._store is None:
            self._store = self._load_store()
        return self._store

    def reset(self, *, clear_persisted: bool = True) -> None:
        settings = get_settings()
        if clear_persisted and settings.ledger_backend == "json":
            settings.ledger_path.unlink(missing_ok=True)
        if clear_persisted and settings.ledger_backend == "postgres":
            self._clear_postgres_snapshot()
        self._store = self._build_store()

    def reload(self) -> InMemoryLedger:
        self._store = self._load_store()
        return self._store

    def save(self) -> None:
        settings = get_settings()
        if self._store is None or self._persisting:
            return

        self._persisting = True
        try:
            payload = self._serialize_store(self._store)
            if settings.ledger_backend == "json":
                settings.ledger_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = Path(f"{settings.ledger_path}.tmp")
                tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                tmp_path.replace(settings.ledger_path)
            elif settings.ledger_backend == "postgres":
                self._save_postgres_snapshot(payload)
        finally:
            self._persisting = False

    def _load_store(self) -> InMemoryLedger:
        settings = get_settings()
        if settings.ledger_backend == "json" and settings.ledger_path.exists():
            payload = json.loads(settings.ledger_path.read_text(encoding="utf-8"))
            return self._deserialize_store(payload)
        if settings.ledger_backend == "postgres":
            payload = self._load_postgres_snapshot()
            if payload is not None:
                return self._deserialize_store(payload)
        return self._build_store()

    def _serialize_store(self, store: InMemoryLedger) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "stores": {
                field.name: [
                    {
                        "key": STORE_CODECS[field.name].key_encoder(key),
                        "value": STORE_CODECS[field.name].value_encoder(value),
                    }
                    for key, value in dict(getattr(store, field.name)).items()
                ]
                for field in fields(InMemoryLedger)
            },
        }

    def _deserialize_store(self, payload: dict[str, Any]) -> InMemoryLedger:
        store = InMemoryLedger()
        for field in fields(InMemoryLedger):
            codec = STORE_CODECS[field.name]
            entries = payload.get("stores", {}).get(field.name, [])
            loaded = {
                codec.key_decoder(entry["key"]): codec.value_decoder(entry["value"])
                for entry in entries
            }
            setattr(store, field.name, loaded)
        seed_templates(store)
        return self._wrap_store(store)

    def _connect_postgres(self):
        settings = get_settings()
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required when DROS_LEDGER_BACKEND=postgres") from exc
        return psycopg.connect(settings.postgres_dsn, autocommit=True)

    def _ensure_postgres_snapshot_table(self, conn) -> None:
        settings = get_settings()
        from psycopg import sql

        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(settings.postgres_schema)))
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {}.ledger_snapshots (
                        snapshot_key text PRIMARY KEY,
                        payload jsonb NOT NULL,
                        updated_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                ).format(sql.Identifier(settings.postgres_schema))
            )

    def _load_postgres_snapshot(self) -> dict[str, Any] | None:
        settings = get_settings()
        from psycopg import sql

        with self._connect_postgres() as conn:
            self._ensure_postgres_snapshot_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT payload FROM {}.ledger_snapshots WHERE snapshot_key = %s").format(
                        sql.Identifier(settings.postgres_schema)
                    ),
                    (self._POSTGRES_SNAPSHOT_KEY,),
                )
                row = cur.fetchone()

        if row is None:
            return None

        payload = row[0]
        if isinstance(payload, str):
            return json.loads(payload)
        return payload

    def _save_postgres_snapshot(self, payload: dict[str, Any]) -> None:
        settings = get_settings()
        from psycopg import sql

        with self._connect_postgres() as conn:
            self._ensure_postgres_snapshot_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO {}.ledger_snapshots (snapshot_key, payload, updated_at)
                        VALUES (%s, %s::jsonb, now())
                        ON CONFLICT (snapshot_key)
                        DO UPDATE SET
                            payload = EXCLUDED.payload,
                            updated_at = EXCLUDED.updated_at
                        """
                    ).format(sql.Identifier(settings.postgres_schema)),
                    (self._POSTGRES_SNAPSHOT_KEY, json.dumps(payload, ensure_ascii=False)),
                )

    def _clear_postgres_snapshot(self) -> None:
        settings = get_settings()
        from psycopg import sql

        with self._connect_postgres() as conn:
            self._ensure_postgres_snapshot_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DELETE FROM {}.ledger_snapshots WHERE snapshot_key = %s").format(
                        sql.Identifier(settings.postgres_schema)
                    ),
                    (self._POSTGRES_SNAPSHOT_KEY,),
                )

    def _build_store(self) -> InMemoryLedger:
        store = InMemoryLedger()
        seed_templates(store)
        return self._wrap_store(store)

    def _wrap_store(self, store: InMemoryLedger) -> InMemoryLedger:
        for field in fields(InMemoryLedger):
            current = getattr(store, field.name)
            if not isinstance(current, PersistentDict):
                setattr(store, field.name, PersistentDict(dict(current), self.save))
        return store


_LEDGER_PROVIDER = LedgerProvider()


def get_memory_store() -> InMemoryLedger:
    return _LEDGER_PROVIDER.get_store()


def reset_memory_store(*, clear_persisted: bool = True) -> None:
    _LEDGER_PROVIDER.reset(clear_persisted=clear_persisted)


def reload_memory_store() -> InMemoryLedger:
    return _LEDGER_PROVIDER.reload()


def append_audit_event(
    store: InMemoryLedger,
    *,
    project_id: UUID | None,
    event_type: str,
    target_kind: LineageKind,
    target_id: UUID | None,
    payload_json: dict[str, Any],
    actor_id: UUID | None = None,
    actor_type: ActorType | None = None,
    trace_id: str | None = None,
    request_id: str | None = None,
) -> AuditEventRead:
    context = current_auth_context()
    now = utcnow()
    prev_hash = None
    if store.audit_events:
        last_event = list(store.audit_events.values())[-1]
        prev_hash = last_event.event_hash
    hash_payload = json.dumps(
        {
            "project_id": str(project_id) if project_id else None,
            "event_type": event_type,
            "target_kind": target_kind.value,
            "target_id": str(target_id) if target_id else None,
            "payload_json": payload_json,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    project = store.projects.get(project_id) if project_id is not None else None
    resolved_tenant_id = project.tenant_id if project is not None else context.tenant_id
    resolved_actor_id = actor_id if actor_id is not None else context.principal_id
    resolved_actor_type = actor_type
    if resolved_actor_type is None:
        resolved_actor_type = ActorType.USER if resolved_actor_id is not None else ActorType.SYSTEM
    event = AuditEventRead(
        id=UUID(bytes=sha256(hash_payload).digest()[:16]),
        tenant_id=resolved_tenant_id,
        project_id=project_id,
        actor_id=resolved_actor_id,
        actor_type=resolved_actor_type,
        event_type=event_type,
        target_kind=target_kind,
        target_id=target_id,
        request_id=request_id or context.request_id,
        trace_id=trace_id or context.trace_id,
        payload_json=payload_json,
        prev_hash=prev_hash,
        event_hash=sha256((prev_hash or "").encode("utf-8") + hash_payload).hexdigest(),
        created_at=now,
    )
    store.audit_events[event.id] = event
    return event


class BaseRepository:
    """Repository ownership declaration for a bounded context."""

    store_names: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.store = get_memory_store()
        self.default_compliance_level = ComplianceLevel.INTERNAL

    @property
    def auth_context(self):
        return current_auth_context()

    @property
    def tenant_id(self) -> UUID:
        return self.auth_context.tenant_id

    @property
    def principal_id(self) -> UUID:
        return self.auth_context.principal_id

    @property
    def actor_id(self) -> UUID:
        return self.auth_context.principal_id

    @property
    def request_id(self) -> str | None:
        return self.auth_context.request_id

    @property
    def trace_id(self) -> str | None:
        return self.auth_context.trace_id

    @property
    def project_role(self):
        return self.auth_context.project_role

    @property
    def scope_tokens(self) -> tuple[str, ...]:
        return self.auth_context.scope_tokens

    def is_dev_default_context(self) -> bool:
        return self.auth_context.auth_source == "dev_default"

    def has_scopes(self, *required_scopes: str) -> bool:
        if self.is_dev_default_context():
            return True
        available = set(self.scope_tokens)
        return all(scope in available for scope in required_scopes)

    def require_scopes(self, *required_scopes: str) -> None:
        if not required_scopes or self.is_dev_default_context():
            return
        available = set(self.scope_tokens)
        missing = [scope for scope in required_scopes if scope not in available]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing required scopes: {', '.join(missing)}",
            )

    def effective_project_scopes(self, project_id: UUID) -> tuple[str, ...]:
        project = self.store.projects.get(project_id)
        if project is None or project.tenant_id != self.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"project {project_id} not found")
        if self.is_dev_default_context():
            return self.scope_tokens
        membership = self.store.project_members.get((project_id, self.principal_id))
        if project.owner_id != self.principal_id and membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"principal {self.principal_id} has no access to project {project_id}",
            )
        membership_scopes = self._membership_scope_tokens(project_id, membership, owner_id=project.owner_id)
        principal_scopes = set(self.scope_tokens)
        return tuple(scope for scope in membership_scopes if scope in principal_scopes)

    def require_project_scopes(self, project_id: UUID, *required_scopes: str) -> None:
        if not required_scopes or self.is_dev_default_context():
            return
        available = set(self.effective_project_scopes(project_id))
        missing = [scope for scope in required_scopes if scope not in available]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing required project scopes: {', '.join(missing)}",
            )

    def list_accessible_projects(self) -> list[ProjectRead]:
        projects = [
            project
            for project in self.store.projects.values()
            if project.tenant_id == self.tenant_id
        ]
        if self.is_dev_default_context():
            return projects
        memberships = {
            project_id
            for (project_id, principal_id), membership in self.store.project_members.items()
            if principal_id == self.principal_id and membership.role.value
        }
        return [
            project
            for project in projects
            if project.owner_id == self.principal_id or project.id in memberships
        ]

    def require_project(self, project_id: UUID, *, required_scopes: tuple[str, ...] = ()) -> ProjectRead:
        project = self.store.projects.get(project_id)
        if project is None or project.tenant_id != self.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"project {project_id} not found")
        if self.is_dev_default_context():
            return project
        membership = self.store.project_members.get((project_id, self.principal_id))
        if project.owner_id != self.principal_id and membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"principal {self.principal_id} has no access to project {project_id}",
            )
        self.require_project_scopes(project_id, *required_scopes)
        return project

    def require_project_scoped(
        self,
        store_name: str,
        project_id: UUID,
        object_id: UUID,
        label: str,
        *,
        required_scopes: tuple[str, ...] = (),
    ) -> Any:
        self.require_project(project_id, required_scopes=required_scopes)
        store = getattr(self.store, store_name)
        item = store.get(object_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} {object_id} not found")

        item_project_id = getattr(item, "project_id", None)
        item_tenant_id = getattr(item, "tenant_id", self.tenant_id)
        if item_project_id != project_id or item_tenant_id != self.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} {object_id} not found")
        return item

    def _membership_scope_tokens(
        self,
        project_id: UUID,
        membership: ProjectMemberRead | None,
        *,
        owner_id: UUID,
    ) -> tuple[str, ...]:
        if membership is not None:
            tokens_raw = membership.scopes_json.get("scope_tokens")
            if isinstance(tokens_raw, list) and all(isinstance(item, str) and item.strip() for item in tokens_raw):
                return tuple(dict.fromkeys(item.strip() for item in tokens_raw))
            return ROLE_SCOPE_TOKENS[membership.role]
        if owner_id == self.principal_id:
            return ROLE_SCOPE_TOKENS[ProjectRole.OWNER]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"principal {self.principal_id} has no access to project {project_id}",
        )

    @classmethod
    def describe(cls) -> tuple[str, ...]:
        return cls.store_names
