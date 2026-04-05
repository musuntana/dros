from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ..schemas.api import AuditEventDetailResponse, AuditEventListResponse, AuditReplayResponse
from .base import BaseService


@dataclass(slots=True)
class AuditService(BaseService):
    repository: object

    def list_events(self, project_id: UUID, *, limit: int, offset: int) -> AuditEventListResponse:
        self._require_project(project_id, "audit:read")
        events = [
            event
            for event in self.repository.store.audit_events.values()
            if event.project_id == project_id
        ]
        events.sort(key=lambda event: event.created_at, reverse=True)
        return AuditEventListResponse(events=self.paginate(events, limit=limit, offset=offset))

    def get_event(self, project_id: UUID, event_id: UUID) -> AuditEventDetailResponse:
        self._require_project(project_id, "audit:read")
        event = self.repository.require_project_scoped(
            "audit_events",
            project_id,
            event_id,
            "audit event",
            required_scopes=("audit:read",),
        )
        return AuditEventDetailResponse(event=event)

    def replay(self) -> AuditReplayResponse:
        self.require_scopes("audit:read")
        previous = None
        for event in self.repository.store.audit_events.values():
            if event.prev_hash != previous:
                return AuditReplayResponse(valid=False, checked_count=0, first_invalid_event_id=event.id)
            previous = event.event_hash
        return AuditReplayResponse(
            valid=True,
            checked_count=len(self.repository.store.audit_events),
            first_invalid_event_id=None,
        )

    def _require_project(self, project_id: UUID, *required_scopes: str) -> None:
        self.repository.require_project(project_id, required_scopes=tuple(required_scopes))
