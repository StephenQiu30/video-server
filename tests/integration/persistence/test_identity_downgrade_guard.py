"""Revision 0004 downgrade is fail-closed once identity facts exist."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._identity import (
    clear_identity_rows,
    current_revision,
    insert_access_token,
    insert_user,
    row_counts,
    schema_fingerprint,
)
from tests.integration.persistence._resolution_aggregate import insert_aggregate
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration

_CONSTRAINT = "ck_identity_downgrade_requires_empty"
_TABLES = (
    "users",
    "access_tokens",
    "jobs",
    "source_resolution_requests",
    "job_events",
    "outbox_messages",
)


def _seed_user(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_user(connection)


def _seed_token(engine: Engine) -> None:
    with engine.begin() as connection:
        insert_user(connection)
        insert_access_token(connection)


@pytest.mark.parametrize(
    "seed",
    [_seed_user, _seed_token, insert_aggregate],
    ids=["user", "access-token", "aggregate"],
)
def test_0004_downgrade_rejects_identity_facts_without_partial_ddl(
    migrated_database: Engine,
    alembic_config: Config,
    seed: Callable[[Engine], None],
) -> None:
    try:
        seed(migrated_database)
        before = (
            set(inspect(migrated_database).get_table_names()),
            _existing_counts(migrated_database),
            schema_fingerprint(migrated_database),
        )

        with pytest.raises(IntegrityError) as rejected:
            command.downgrade(alembic_config, "0003_rights_attestation_history")

        assert_constraint(rejected.value, name=_CONSTRAINT, sqlstate="23514")
        assert current_revision(migrated_database) == "0004_identity_owner_uuid"
        after = (
            set(inspect(migrated_database).get_table_names()),
            _existing_counts(migrated_database),
            schema_fingerprint(migrated_database),
        )
        assert after == before
    finally:
        if "users" in inspect(migrated_database).get_table_names():
            clear_identity_rows(migrated_database)


def _existing_counts(engine: Engine) -> tuple[int, ...]:
    existing = set(inspect(engine).get_table_names())
    return row_counts(engine, tuple(table for table in _TABLES if table in existing))
