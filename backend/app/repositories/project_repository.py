from .base import BaseRepository


class ProjectRepository(BaseRepository):
    """Owns project aggregate persistence."""

    store_names = ("projects", "project_members")
