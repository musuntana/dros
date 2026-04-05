from .base import BaseRepository


class ArtifactRepository(BaseRepository):
    """Owns artifact metadata and explicit lineage edges."""

    store_names = ("artifacts", "lineage_edges")
