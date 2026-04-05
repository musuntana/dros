from .base import BaseRepository


class ReviewRepository(BaseRepository):
    """Owns persisted review state."""

    store_names = ("reviews",)
