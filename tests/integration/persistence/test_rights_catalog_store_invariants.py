"""Full-snapshot and transaction invariants for catalog imports."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine, text

from tests.integration.persistence._rights_catalog import catalog_entry, make_catalog
from video_server.persistence.rights_catalog import (
    PostgresRightsCatalogStore,
    RightsCatalogPersistenceError,
)

pytestmark = pytest.mark.integration

_V1 = "rights-2026-07-18.1"
_V2 = "rights-2026-07-19.1"


def _initial_catalog():  # type: ignore[no-untyped-def]
    return make_catalog(
        catalog_entry(version=_V1, locale="zh-CN"),
        catalog_entry(version=_V1, locale="en-US"),
    )


def _snapshot(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    """
                    SELECT version, locale, statement_sha256, effective_at, superseded_at
                    FROM rights_statement_catalog
                    ORDER BY locale, effective_at
                    """
                )
            ).tuples()
        )


def test_store_rejects_supersede_without_same_time_successor(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    initial = _initial_catalog()
    store.import_catalog(initial)
    before = _snapshot(migrated_database)
    zh_statement = initial.entries[0].statement.statement

    missing_successor = make_catalog(
        catalog_entry(
            version=_V1,
            locale="zh-CN",
            statement=zh_statement,
            superseded_at="2026-07-19T00:00:00Z",
        ),
        catalog_entry(version=_V1, locale="en-US"),
    )
    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        store.import_catalog(missing_successor)

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    assert _snapshot(migrated_database) == before


def test_store_rejects_gap_between_superseded_and_successor(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    initial = _initial_catalog()
    store.import_catalog(initial)
    before = _snapshot(migrated_database)
    zh_statement = initial.entries[0].statement.statement

    gapped_transition = make_catalog(
        catalog_entry(
            version=_V1,
            locale="zh-CN",
            statement=zh_statement,
            superseded_at="2026-07-19T00:00:00Z",
        ),
        catalog_entry(
            version=_V2,
            locale="zh-CN",
            effective_at="2026-07-20T00:00:00Z",
        ),
        catalog_entry(version=_V1, locale="en-US"),
    )
    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        store.import_catalog(gapped_transition)

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    assert _snapshot(migrated_database) == before


def test_store_rejects_snapshot_that_omits_durable_history(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    zh_v2 = catalog_entry(
        version=_V2,
        locale="zh-CN",
        effective_at="2026-07-19T00:00:00Z",
    )
    en_v1 = catalog_entry(version=_V1, locale="en-US")
    store.import_catalog(
        make_catalog(
            catalog_entry(
                version=_V1,
                locale="zh-CN",
                superseded_at="2026-07-19T00:00:00Z",
            ),
            zh_v2,
            en_v1,
        )
    )
    before = _snapshot(migrated_database)

    omitted_history = make_catalog(zh_v2, en_v1)
    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        store.import_catalog(omitted_history)

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    assert _snapshot(migrated_database) == before


def test_store_rejects_autocommit_engine_before_partial_write(
    migrated_database: Engine,
) -> None:
    normal_store = PostgresRightsCatalogStore(migrated_database)
    initial = _initial_catalog()
    normal_store.import_catalog(initial)
    before = _snapshot(migrated_database)
    zh_statement = initial.entries[0].statement.statement

    partially_applicable = make_catalog(
        catalog_entry(
            version=_V1,
            locale="zh-CN",
            statement=zh_statement,
            superseded_at="2026-07-19T00:00:00Z",
        ),
        catalog_entry(version=_V2, locale="zh-CN", effective_at="2026-07-19T00:00:00Z"),
        catalog_entry(version=_V1, locale="en-US"),
        catalog_entry(version=_V2, locale="en-US", effective_at="2026-07-19T00:00:00Z"),
    )
    autocommit_engine = migrated_database.execution_options(isolation_level="AUTOCOMMIT")
    store = PostgresRightsCatalogStore(autocommit_engine)

    with pytest.raises(RightsCatalogPersistenceError) as unavailable:
        store.import_catalog(partially_applicable)

    assert unavailable.value.code == "RIGHTS_CATALOG_STORAGE_UNAVAILABLE"
    assert unavailable.value.retryable is True
    assert _snapshot(migrated_database) == before


def test_store_safely_maps_connection_pool_timeout(migrated_database: Engine) -> None:
    initial = _initial_catalog()
    PostgresRightsCatalogStore(migrated_database).import_catalog(initial)
    before = _snapshot(migrated_database)
    constrained_engine = create_engine(
        migrated_database.url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.01,
    )

    try:
        with (
            constrained_engine.connect(),
            pytest.raises(RightsCatalogPersistenceError) as unavailable,
        ):
            PostgresRightsCatalogStore(constrained_engine).import_catalog(initial)
    finally:
        constrained_engine.dispose()

    assert unavailable.value.code == "RIGHTS_CATALOG_STORAGE_UNAVAILABLE"
    assert unavailable.value.detail == "The rights catalog storage is temporarily unavailable."
    assert "postgresql" not in str(unavailable.value).lower()
    assert _snapshot(migrated_database) == before
