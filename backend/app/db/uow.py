"""Unit of Work — transaction boundary for repository operations."""

from __future__ import annotations

from types import TracebackType
from typing import Any

from psycopg import Connection


class PostgresUnitOfWork:
    """Acquires a pooled connection, binds RLS context, and manages the transaction."""

    conn: Connection

    def __enter__(self) -> PostgresUnitOfWork:
        from ..auth import current_auth_context

        from .context import bind_rls
        from .pool import get_pool

        pool = get_pool()
        self.conn = pool.getconn()
        self.conn.autocommit = False
        ctx = current_auth_context()
        bind_rls(self.conn, ctx.tenant_id, ctx.principal_id)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        from .pool import get_pool

        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            pool = get_pool()
            self.conn.autocommit = True
            pool.putconn(self.conn)


class MemoryUnitOfWork:
    """No-op unit of work for the in-memory / json / snapshot backends."""

    conn: Any = None

    def __enter__(self) -> MemoryUnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass
