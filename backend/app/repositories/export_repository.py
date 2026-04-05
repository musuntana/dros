from .base import BaseRepository


class ExportRepository(BaseRepository):
    """Owns export job metadata."""

    store_names = ("export_jobs",)
