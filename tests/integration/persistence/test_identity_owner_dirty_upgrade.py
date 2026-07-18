"""Revision 0004 must atomically reject every legacy aggregate owner."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._identity import current_revision, row_counts, schema_fingerprint
from tests.integration.persistence._legacy_resolution_aggregate import insert_legacy_aggregate
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration

_CONSTRAINT = "ck_owner_uuid_migration_requires_empty_aggregate"
_TABLES = ("jobs", "source_resolution_requests", "job_events", "outbox_messages")


def test_uuid_looking_text_owner_still_blocks_0004_upgrade_atomically(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    command.downgrade(alembic_config, "0003_rights_attestation_history")
    try:
        insert_legacy_aggregate(migrated_database)
        before = (
            _owner_types(migrated_database),
            row_counts(migrated_database, _TABLES),
            schema_fingerprint(migrated_database),
        )

        with pytest.raises(IntegrityError) as rejected:
            command.upgrade(alembic_config, "head")

        assert_constraint(rejected.value, name=_CONSTRAINT, sqlstate="23514")
        assert current_revision(migrated_database) == "0003_rights_attestation_history"
        assert not ({"users", "access_tokens"} & set(inspect(migrated_database).get_table_names()))
        assert (
            _owner_types(migrated_database),
            row_counts(migrated_database, _TABLES),
            schema_fingerprint(migrated_database),
        ) == before
        with migrated_database.connect() as connection:
            owner = str(connection.scalar(text("SELECT owner_id FROM jobs")))
        assert owner == "8f83e1c4-9a31-4c26-b2de-9a7f53dd6ed1"
    finally:
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")


def _owner_types(engine: Engine) -> tuple[str, ...]:
    inspector = inspect(engine)
    return tuple(
        str(
            next(
                item["type"] for item in inspector.get_columns(table) if item["name"] == "owner_id"
            )
        )
        for table in _TABLES
    )
