"""Migration round-trip contract."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

pytestmark = pytest.mark.integration


def test_empty_database_downgrades_to_base(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    assert "rights_statement_catalog" in inspect(migrated_database).get_table_names()

    command.downgrade(alembic_config, "base")

    assert "rights_statement_catalog" not in inspect(migrated_database).get_table_names()
