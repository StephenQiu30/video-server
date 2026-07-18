"""Revision 0004 identity and UUID owner migration contract."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

pytestmark = pytest.mark.integration

_OWNER_TABLES = ("jobs", "source_resolution_requests", "job_events", "outbox_messages")


def test_every_aggregate_owner_is_a_required_uuid_user_reference(
    migrated_database: Engine,
) -> None:
    inspector = inspect(migrated_database)
    for table in _OWNER_TABLES:
        owner = next(item for item in inspector.get_columns(table) if item["name"] == "owner_id")
        assert isinstance(owner["type"], PostgreSQLUUID)
        assert owner["nullable"] is False
        matching = [
            item
            for item in inspector.get_foreign_keys(table)
            if item["constrained_columns"] == ["owner_id"]
            and item["referred_table"] == "users"
            and item["referred_columns"] == ["id"]
        ]
        assert len(matching) == 1
        checks = {item["name"] for item in inspector.get_check_constraints(table)}
        assert f"ck_{table}_owner_format" not in checks


def test_empty_database_can_cycle_through_identity_revision(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    try:
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
        tables = set(inspect(migrated_database).get_table_names())
        assert {"users", "access_tokens", *_OWNER_TABLES} <= tables

        command.downgrade(alembic_config, "base")
        assert "users" not in inspect(migrated_database).get_table_names()
    finally:
        command.upgrade(alembic_config, "head")
