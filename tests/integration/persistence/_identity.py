"""PostgreSQL identity fixtures shared by migration and aggregate tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Connection, Engine, inspect, text

from tests.identity_contract import OTHER_USER_ID, USER_ID

__all__ = ["OTHER_USER_ID", "USER_ID"]

SESSION_TOKEN = "s" * 43
SESSION_CREATED_AT = datetime(2026, 7, 18, tzinfo=UTC)


def insert_user(
    connection: Connection,
    user_id: UUID = USER_ID,
    *,
    email: str | None = None,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO users (
                id, email, hashed_password, is_active, is_superuser, is_verified
            ) VALUES (
                :id, :email, :hashed_password, true, false, true
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": user_id,
            "email": email or f"owner-{user_id.hex}@example.test",
            "hashed_password": "$argon2id$v=19$test-only",
        },
    )


def insert_access_token(
    connection: Connection,
    *,
    user_id: UUID = USER_ID,
    token: str = SESSION_TOKEN,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO access_tokens (token, created_at, user_id)
            VALUES (:token, :created_at, :user_id)
            """
        ),
        {"token": token, "created_at": SESSION_CREATED_AT, "user_id": user_id},
    )


def ensure_user_for_owner(connection: Connection, owner_id: object) -> None:
    if connection.scalar(text("SELECT to_regclass('users')")) is None:
        return
    try:
        user_id = owner_id if isinstance(owner_id, UUID) else UUID(str(owner_id))
    except (TypeError, ValueError):
        return
    insert_user(connection, user_id)


def clear_identity_rows(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    ordered = (
        "outbox_messages",
        "source_resolution_requests",
        "job_events",
        "jobs",
        "access_tokens",
        "users",
    )
    with engine.begin() as connection:
        for table in ordered:
            if table in tables:
                connection.execute(text(f"DELETE FROM {table}"))


def current_revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version_num FROM alembic_version")))


def row_counts(engine: Engine, tables: tuple[str, ...]) -> tuple[int, ...]:
    with engine.connect() as connection:
        return tuple(
            int(connection.scalar(text(f"SELECT count(*) FROM {table}")) or 0) for table in tables
        )


def schema_fingerprint(engine: Engine) -> tuple[tuple[str, ...], ...]:
    """Return stable public-schema DDL evidence for atomic migration assertions."""

    queries = (
        """
        SELECT c.relname || ':' || a.attname || ':' ||
               pg_catalog.format_type(a.atttypid, a.atttypmod) || ':' ||
               a.attnotnull::text
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p')
          AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum
        """,
        """
        SELECT conrelid::regclass::text || ':' || conname || ':' || pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE connamespace='public'::regnamespace
        ORDER BY conrelid::regclass::text, conname
        """,
        """
        SELECT tablename || ':' || indexname || ':' || indexdef
        FROM pg_indexes WHERE schemaname='public'
        ORDER BY tablename, indexname
        """,
        """
        SELECT event_object_table || ':' || trigger_name || ':' || action_statement
        FROM information_schema.triggers WHERE trigger_schema='public'
        ORDER BY event_object_table, trigger_name
        """,
        """
        SELECT proname || ':' || pg_get_functiondef(oid)
        FROM pg_proc WHERE pronamespace='public'::regnamespace
        ORDER BY proname, oid
        """,
    )
    with engine.connect() as connection:
        return tuple(
            tuple(str(value) for value in connection.scalars(text(query))) for query in queries
        )
