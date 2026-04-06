"""RLS context binding for PostgreSQL connections."""

from __future__ import annotations

from uuid import UUID

from psycopg import Connection


def bind_rls(conn: Connection, tenant_id: UUID, principal_id: UUID) -> None:
    """Set LOCAL session variables for row-level security.

    Must be called inside an active transaction (autocommit=False).
    SET LOCAL scopes to the current transaction so that returning the
    connection to the pool does not leak tenant context.
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL app.tenant_id = %s", (str(tenant_id),))
        cur.execute("SET LOCAL app.principal_id = %s", (str(principal_id),))
