"""Low-level parameterized SQL helpers for the row-level backend."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import Connection, sql
from psycopg.rows import dict_row


def insert_row(conn: Connection, table: str, data: dict[str, Any]) -> None:
    """INSERT a single row.  *data* keys are column names, values are parameters."""
    cols = list(data.keys())
    query = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
        table=sql.Identifier(table),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in cols),
        vals=sql.SQL(", ").join(sql.Placeholder() for _ in cols),
    )
    with conn.cursor() as cur:
        cur.execute(query, list(data.values()))


def select_by_id(conn: Connection, table: str, row_id: UUID) -> dict[str, Any] | None:
    """SELECT a single row by primary key ``id``."""
    query = sql.SQL("SELECT * FROM {table} WHERE id = %s").format(
        table=sql.Identifier(table),
    )
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (row_id,))
        return cur.fetchone()


def select_where(
    conn: Connection,
    table: str,
    where: dict[str, Any],
    *,
    order_by: str | None = None,
    order_desc: bool = True,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    """SELECT rows matching all *where* conditions (AND)."""
    parts: list[sql.Composable] = [
        sql.SQL("SELECT * FROM {table}").format(table=sql.Identifier(table)),
    ]
    if where:
        clauses = sql.SQL(" AND ").join(
            sql.SQL("{col} = %s").format(col=sql.Identifier(k)) for k in where
        )
        parts.append(sql.SQL("WHERE ") + clauses)
    if order_by is not None:
        direction = sql.SQL("DESC") if order_desc else sql.SQL("ASC")
        parts.append(
            sql.SQL("ORDER BY {col} ").format(col=sql.Identifier(order_by)) + direction
        )
    if limit is not None:
        parts.append(sql.SQL("LIMIT %s"))
    if offset is not None:
        parts.append(sql.SQL("OFFSET %s"))

    query = sql.SQL(" ").join(parts)
    params: list[Any] = list(where.values())
    if limit is not None:
        params.append(limit)
    if offset is not None:
        params.append(offset)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def exists_where(conn: Connection, table: str, where: dict[str, Any]) -> bool:
    """Return True if at least one row matches all *where* conditions."""
    clauses = sql.SQL(" AND ").join(
        sql.SQL("{col} = %s").format(col=sql.Identifier(k)) for k in where
    )
    query = sql.SQL("SELECT EXISTS(SELECT 1 FROM {table} WHERE {clauses})").format(
        table=sql.Identifier(table),
        clauses=clauses,
    )
    with conn.cursor() as cur:
        cur.execute(query, list(where.values()))
        row = cur.fetchone()
        return bool(row and row[0])


def insert_if_not_exists(conn: Connection, table: str, data: dict[str, Any]) -> bool:
    """INSERT a row only if its primary key ``id`` is not already present.

    Returns True if a row was inserted, False if it already existed.
    """
    row_id = data.get("id")
    if row_id is not None and exists_where(conn, table, {"id": row_id}):
        return False
    insert_row(conn, table, data)
    return True


def update_columns(
    conn: Connection,
    table: str,
    row_id: UUID,
    data: dict[str, Any],
) -> None:
    """UPDATE specific columns on a single row by primary key."""
    sets = sql.SQL(", ").join(
        sql.SQL("{col} = %s").format(col=sql.Identifier(k)) for k in data
    )
    query = sql.SQL("UPDATE {table} SET {sets} WHERE id = %s").format(
        table=sql.Identifier(table),
        sets=sets,
    )
    params = list(data.values()) + [row_id]
    with conn.cursor() as cur:
        cur.execute(query, params)
