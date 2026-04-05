from .base import BaseRepository


class EvidenceRepository(BaseRepository):
    """Owns evidence source normalization and binding metadata."""

    store_names = ("evidence_sources", "evidence_chunks", "evidence_links")
