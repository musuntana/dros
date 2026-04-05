from __future__ import annotations

import pytest

from backend.app import dependencies
from backend.app.auth import clear_auth_caches
from backend.app.repositories.base import reset_memory_store
from backend.app.settings import get_settings


@pytest.fixture(autouse=True)
def reset_state() -> None:
    get_settings.cache_clear()
    clear_auth_caches()
    reset_memory_store()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()
    yield
    get_settings.cache_clear()
    clear_auth_caches()
    reset_memory_store()
    for name in dir(dependencies):
        dependency = getattr(dependencies, name)
        if callable(dependency) and hasattr(dependency, "cache_clear"):
            dependency.cache_clear()
