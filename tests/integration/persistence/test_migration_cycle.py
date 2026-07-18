"""Migration round-trip contract."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

pytestmark = pytest.mark.integration

_AGGREGATE_TABLES = {
    "jobs",
    "source_resolution_requests",
    "job_events",
    "outbox_messages",
}


def test_empty_database_downgrades_to_base(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    assert "rights_statement_catalog" in inspect(migrated_database).get_table_names()

    command.downgrade(alembic_config, "base")

    assert "rights_statement_catalog" not in inspect(migrated_database).get_table_names()


def test_resolution_aggregate_downgrades_to_catalog(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    assert set(inspect(migrated_database).get_table_names()) >= _AGGREGATE_TABLES

    command.downgrade(alembic_config, "0001_rights_catalog")

    tables = set(inspect(migrated_database).get_table_names())
    assert "rights_statement_catalog" in tables
    assert not (_AGGREGATE_TABLES & tables)
