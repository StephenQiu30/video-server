"""Concurrent rights-catalog writer contract."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._rights_catalog import catalog_entry, make_catalog
from video_server.persistence.rights_catalog import (
    CatalogImportResult,
    PostgresRightsCatalogStore,
    RightsCatalogPersistenceError,
)
from video_server.source.rights import RightsCatalog

pytestmark = pytest.mark.integration


def _import_after_barrier(
    store: PostgresRightsCatalogStore,
    catalog: RightsCatalog,
    barrier: Barrier,
) -> CatalogImportResult | RightsCatalogPersistenceError:
    barrier.wait(timeout=5)
    try:
        return store.import_catalog(catalog)
    except RightsCatalogPersistenceError as error:
        return error


def test_same_locale_concurrent_import_has_one_winner_and_stable_conflict(
    migrated_database: Engine,
) -> None:
    store = PostgresRightsCatalogStore(migrated_database)
    barrier = Barrier(2)
    shared_entry = catalog_entry(version="rights-2026-07-18.1", locale="en-US")
    catalogs = (
        make_catalog(
            catalog_entry(version="rights-2026-07-18.1"),
            shared_entry,
        ),
        make_catalog(
            catalog_entry(
                version="rights-2026-07-19.1",
                effective_at="2026-07-19T00:00:00Z",
            ),
            shared_entry,
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda catalog: _import_after_barrier(store, catalog, barrier),
                catalogs,
            )
        )

    successes = [result for result in results if isinstance(result, CatalogImportResult)]
    conflicts = [result for result in results if isinstance(result, RightsCatalogPersistenceError)]
    assert successes == [CatalogImportResult(2, 0, 0)]
    assert len(conflicts) == 1
    assert conflicts[0].code == "RIGHTS_CATALOG_CONFLICT"
    with migrated_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM rights_statement_catalog")) == 2
