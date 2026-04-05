from .base import BaseRepository


class WorkflowRepository(BaseRepository):
    """Owns workflow state and analysis run metadata."""

    store_names = (
        "workflow_instances",
        "workflow_tasks",
        "analysis_runs",
    )
