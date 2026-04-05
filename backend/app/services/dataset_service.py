from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from ..repositories.base import append_audit_event
from ..schemas.api import (
    CreateDatasetResponse,
    CreateDatasetSnapshotRequest,
    CreateDatasetSnapshotResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetSnapshotListResponse,
    ImportPublicDatasetRequest,
    RegisterUploadDatasetRequest,
)
from ..schemas.domain import DatasetRead, DatasetSnapshotRead
from ..schemas.enums import (
    DatasetSourceKind,
    DeidStatus,
    LicenseClass,
    LineageKind,
    PhiScanStatus,
    PiiLevel,
)
from .base import BaseService


@dataclass(slots=True)
class DatasetService(BaseService):
    repository: object

    def import_public_dataset(self, project_id: UUID, payload: ImportPublicDatasetRequest) -> CreateDatasetResponse:
        self._require_project(project_id, "datasets:write")
        source_kind = self._parse_source_kind(payload.source_kind)
        now = self.now()
        dataset = DatasetRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            source_kind=source_kind,
            display_name=payload.accession,
            source_ref=payload.accession,
            pii_level=PiiLevel.NONE,
            license_class=LicenseClass.PUBLIC,
            current_snapshot_id=None,
            created_at=now,
            updated_at=now,
        )
        self.repository.store.datasets[dataset.id] = dataset
        snapshot = self._create_snapshot_record(
            dataset=dataset,
            object_uri=f"public://{source_kind.value}/{payload.accession}",
            input_hash_sha256=sha256(payload.accession.encode("utf-8")).hexdigest(),
            row_count=None,
            column_schema_json={"source": payload.accession},
            deid_status=DeidStatus.NOT_REQUIRED,
            phi_scan_status=PhiScanStatus.PASSED,
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="dataset.imported_public",
            target_kind=LineageKind.DATASET,
            target_id=dataset.id,
            payload_json={"accession": payload.accession, "source_kind": source_kind.value},
        )
        return CreateDatasetResponse(dataset=dataset, snapshot=snapshot, workflow_instance_id=None)

    def register_upload_dataset(self, project_id: UUID, payload: RegisterUploadDatasetRequest) -> CreateDatasetResponse:
        self._require_project(project_id, "datasets:write")
        now = self.now()
        dataset = DatasetRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=project_id,
            source_kind=DatasetSourceKind.UPLOAD,
            display_name=payload.display_name,
            source_ref=payload.file_ref,
            pii_level=PiiLevel.LIMITED,
            license_class=LicenseClass.UNKNOWN,
            current_snapshot_id=None,
            created_at=now,
            updated_at=now,
        )
        self.repository.store.datasets[dataset.id] = dataset
        snapshot = self._create_snapshot_record(
            dataset=dataset,
            object_uri=f"upload://{payload.file_ref}",
            input_hash_sha256=sha256(payload.file_ref.encode("utf-8")).hexdigest(),
            row_count=None,
            column_schema_json={},
            deid_status=DeidStatus.PENDING,
            phi_scan_status=PhiScanStatus.PENDING,
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="dataset.registered_upload",
            target_kind=LineageKind.DATASET,
            target_id=dataset.id,
            payload_json={"file_ref": payload.file_ref},
        )
        return CreateDatasetResponse(dataset=dataset, snapshot=snapshot, workflow_instance_id=None)

    def list_datasets(self, project_id: UUID, *, limit: int, offset: int) -> DatasetListResponse:
        self._require_project(project_id, "datasets:read")
        items = sorted(
            [
                dataset
                for dataset in self.repository.store.datasets.values()
                if dataset.project_id == project_id
            ],
            key=lambda dataset: dataset.created_at,
            reverse=True,
        )
        return DatasetListResponse(items=self.paginate(items, limit=limit, offset=offset))

    def get_dataset(self, project_id: UUID, dataset_id: UUID) -> DatasetDetailResponse:
        dataset = self._require_dataset(project_id, dataset_id, "datasets:read")
        current_snapshot = (
            self.repository.store.dataset_snapshots.get(dataset.current_snapshot_id)
            if dataset.current_snapshot_id
            else None
        )
        return DatasetDetailResponse(dataset=dataset, current_snapshot=current_snapshot)

    def create_snapshot(self, project_id: UUID, dataset_id: UUID, payload: CreateDatasetSnapshotRequest) -> CreateDatasetSnapshotResponse:
        dataset = self._require_dataset(project_id, dataset_id, "datasets:write")
        if dataset.source_kind == DatasetSourceKind.UPLOAD:
            deid_status = DeidStatus.PENDING
            phi_scan_status = PhiScanStatus.PENDING
        else:
            deid_status = DeidStatus.NOT_REQUIRED
            phi_scan_status = PhiScanStatus.PASSED
        snapshot = self._create_snapshot_record(
            dataset=dataset,
            object_uri=payload.object_uri,
            input_hash_sha256=payload.input_hash_sha256,
            row_count=payload.row_count,
            column_schema_json=payload.column_schema_json,
            deid_status=deid_status,
            phi_scan_status=phi_scan_status,
        )
        append_audit_event(
            self.repository.store,
            project_id=project_id,
            event_type="dataset.snapshot.created",
            target_kind=LineageKind.DATASET_SNAPSHOT,
            target_id=snapshot.id,
            payload_json={"dataset_id": str(dataset_id), "snapshot_no": snapshot.snapshot_no},
        )
        return CreateDatasetSnapshotResponse(snapshot=snapshot)

    def list_snapshots(self, project_id: UUID, dataset_id: UUID) -> DatasetSnapshotListResponse:
        self._require_dataset(project_id, dataset_id, "datasets:read")
        snapshots = [
            snapshot
            for snapshot in self.repository.store.dataset_snapshots.values()
            if snapshot.project_id == project_id and snapshot.dataset_id == dataset_id
        ]
        snapshots.sort(key=lambda snapshot: snapshot.snapshot_no, reverse=True)
        return DatasetSnapshotListResponse(items=snapshots)

    def _create_snapshot_record(
        self,
        *,
        dataset: DatasetRead,
        object_uri: str,
        input_hash_sha256: str,
        row_count: int | None,
        column_schema_json: dict[str, object],
        deid_status: DeidStatus,
        phi_scan_status: PhiScanStatus,
    ) -> DatasetSnapshotRead:
        snapshot_no = self.repository.store.snapshot_numbers.get(dataset.id, 0) + 1
        self.repository.store.snapshot_numbers[dataset.id] = snapshot_no
        snapshot = DatasetSnapshotRead(
            id=uuid4(),
            tenant_id=self.repository.tenant_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            snapshot_no=snapshot_no,
            object_uri=object_uri,
            input_hash_sha256=input_hash_sha256,
            row_count=row_count,
            column_schema_json=column_schema_json,
            deid_status=deid_status,
            phi_scan_status=phi_scan_status,
            created_at=self.now(),
        )
        self.repository.store.dataset_snapshots[snapshot.id] = snapshot
        self.repository.store.datasets[dataset.id] = dataset.model_copy(
            update={"current_snapshot_id": snapshot.id, "updated_at": self.now()}
        )
        return snapshot

    def _parse_source_kind(self, raw: str) -> DatasetSourceKind:
        try:
            return DatasetSourceKind(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"unsupported dataset source kind: {raw}",
            ) from exc

    def _require_project(self, project_id: UUID, *required_scopes: str) -> object:
        return self.repository.require_project(project_id, required_scopes=tuple(required_scopes))

    def _require_dataset(self, project_id: UUID, dataset_id: UUID, *required_scopes: str) -> DatasetRead:
        return self.repository.require_project_scoped(
            "datasets",
            project_id,
            dataset_id,
            "dataset",
            required_scopes=tuple(required_scopes),
        )
