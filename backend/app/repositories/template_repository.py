from .base import BaseRepository


class TemplateRepository(BaseRepository):
    """Owns analysis template registry metadata."""

    store_names = ("analysis_templates",)
