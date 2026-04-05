from .base import BaseRepository


class AuditRepository(BaseRepository):
    """Owns append-only audit events."""

    store_names = ("audit_events",)
