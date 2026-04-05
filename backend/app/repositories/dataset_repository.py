from .base import BaseRepository


class DatasetRepository(BaseRepository):
    """Owns datasets and immutable snapshots."""

    store_names = ("datasets", "dataset_snapshots")
