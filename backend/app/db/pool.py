"""Connection pool management for the postgres_rowlevel backend."""

from __future__ import annotations

from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def init_pool(
    dsn: str,
    *,
    min_size: int = 2,
    max_size: int = 10,
    schema: str = "dr_os",
) -> None:
    global _pool
    if _pool is not None:
        return
    _pool = ConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        kwargs={"options": f"-c search_path={schema},public"},
    )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("PostgreSQL connection pool is not initialized")
    return _pool
