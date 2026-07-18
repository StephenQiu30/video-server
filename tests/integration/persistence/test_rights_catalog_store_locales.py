"""Supported-locale completeness contract for catalog snapshots."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._rights_catalog import catalog_entry, make_catalog
from video_server.persistence.rights_catalog import (
    PostgresRightsCatalogStore,
    RightsCatalogPersistenceError,
)

pytestmark = pytest.mark.integration


def test_initial_snapshot_must_include_every_supported_locale(
    migrated_database: Engine,
) -> None:
    zh_only = make_catalog(
        catalog_entry(
            version="rights-2026-07-17.1",
            locale="zh-CN",
            effective_at="2026-07-17T00:00:00Z",
            superseded_at="2026-07-18T00:00:00Z",
        ),
        catalog_entry(version="rights-2026-07-18.1", locale="zh-CN"),
    )

    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        PostgresRightsCatalogStore(migrated_database).import_catalog(zh_only)

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    with migrated_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM rights_statement_catalog")) == 0
