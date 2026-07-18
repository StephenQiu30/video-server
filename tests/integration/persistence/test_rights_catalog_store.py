"""Transactional rights-catalog writer contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._rights_catalog import catalog_entry, make_catalog
from video_server.persistence.rights_catalog import (
    CatalogImportResult,
    PostgresRightsCatalogStore,
    RightsCatalogPersistenceError,
)

pytestmark = pytest.mark.integration

_V1 = "rights-2026-07-18.1"
_V2 = "rights-2026-07-19.1"


def _rows(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    """
                    SELECT version, locale, statement, statement_sha256,
                           effective_at, expires_at, superseded_at
                    FROM rights_statement_catalog
                    ORDER BY locale, effective_at
                    """
                )
            ).tuples()
        )


def test_store_imports_and_idempotently_replays_exact_catalog(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    catalog = make_catalog(
        catalog_entry(version=_V1, locale="zh-CN"),
        catalog_entry(version=_V1, locale="en-US"),
    )

    assert store.import_catalog(catalog) == CatalogImportResult(2, 0, 0)
    first_rows = _rows(migrated_database)
    assert len(first_rows) == 2

    assert store.import_catalog(catalog) == CatalogImportResult(0, 2, 0)
    assert _rows(migrated_database) == first_rows


def test_store_rejects_identity_drift_without_mutating_history(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    original = make_catalog(
        catalog_entry(version=_V1, statement="original"),
        catalog_entry(version=_V1, locale="en-US"),
    )
    store.import_catalog(original)
    original_rows = _rows(migrated_database)

    drifted = make_catalog(
        catalog_entry(version=_V1, statement="changed"),
        catalog_entry(version=_V1, locale="en-US"),
    )
    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        store.import_catalog(drifted)

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    assert conflict.value.detail == "The rights catalog conflicts with durable history."
    assert _rows(migrated_database) == original_rows


def test_store_rolls_back_whole_batch_when_one_locale_overlaps(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    store.import_catalog(
        make_catalog(
            catalog_entry(version=_V1, locale="zh-CN"),
            catalog_entry(version=_V1, locale="en-US"),
        )
    )

    conflicting_batch = make_catalog(
        catalog_entry(
            version="rights-2026-07-17.1",
            locale="en-US",
            effective_at="2026-07-17T00:00:00Z",
            superseded_at="2026-07-18T00:00:00Z",
        ),
        catalog_entry(version=_V1, locale="en-US"),
        catalog_entry(version=_V1, locale="zh-CN"),
        catalog_entry(
            version=_V2,
            locale="zh-CN",
            effective_at="2026-07-19T00:00:00Z",
        ),
    )
    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        store.import_catalog(conflicting_batch)

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    assert {(row[0], row[1]) for row in _rows(migrated_database)} == {
        (_V1, "en-US"),
        (_V1, "zh-CN"),
    }


def test_store_atomically_supersedes_then_inserts_adjacent_version(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    statement_v1 = "first statement"
    en_entry = catalog_entry(version=_V1, locale="en-US")
    store.import_catalog(
        make_catalog(
            catalog_entry(version=_V1, statement=statement_v1),
            en_entry,
        )
    )
    transition = make_catalog(
        catalog_entry(
            version=_V1,
            statement=statement_v1,
            superseded_at="2026-07-19T00:00:00Z",
        ),
        catalog_entry(
            version=_V2,
            statement="second statement",
            effective_at="2026-07-19T00:00:00Z",
        ),
        en_entry,
    )

    assert store.import_catalog(transition) == CatalogImportResult(1, 1, 1)
    assert store.import_catalog(transition) == CatalogImportResult(0, 3, 0)

    with migrated_database.connect() as connection:
        current_versions = connection.scalars(
            text(
                """
                SELECT version FROM rights_statement_catalog
                WHERE locale = 'zh-CN'
                  AND effective_at <= :now
                  AND (expires_at IS NULL OR :now < expires_at)
                  AND (superseded_at IS NULL OR :now < superseded_at)
                """
            ),
            {"now": datetime(2026, 7, 20, tzinfo=UTC)},
        ).all()
    assert current_versions == [_V2]
