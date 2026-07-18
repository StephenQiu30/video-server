"""Shared rights-locale lock contract for catalog import and resolution create."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._resolution_create_scopes import (
    scoped_command,
    scoped_store,
)
from tests.integration.persistence._resolution_create_store import (
    RIGHTS_CHANGE_AT,
    MutableClock,
    aggregate_counts,
)
from tests.integration.persistence._rights_catalog import catalog_entry, make_catalog
from video_server.persistence.resolution_create import (
    CreateDisposition,
    CreateResolutionResult,
    PostgresResolutionCreateStore,
    ResolutionCreatePersistenceError,
)
from video_server.persistence.rights_catalog import (
    CatalogImportResult,
    PostgresRightsCatalogStore,
    RightsCatalogPersistenceError,
)
from video_server.source.rights import RightsCatalog

pytestmark = pytest.mark.integration

_V1 = "rights-2026-07-18.1"
_V2 = "rights-2026-07-19.1"
_CHANGE_AT = RIGHTS_CHANGE_AT.isoformat().replace("+00:00", "Z")


def _catalogs() -> tuple[RightsCatalog, RightsCatalog]:
    initial = make_catalog(
        catalog_entry(version=_V1, locale="en-US"),
        catalog_entry(version=_V1, locale="zh-CN"),
    )
    superseding = make_catalog(
        catalog_entry(version=_V1, locale="en-US"),
        catalog_entry(version=_V1, locale="zh-CN", superseded_at=_CHANGE_AT),
        catalog_entry(version=_V2, locale="zh-CN", effective_at=_CHANGE_AT),
    )
    return initial, superseding


def _create_after_barrier(
    store: PostgresResolutionCreateStore,
    barrier: Barrier,
) -> CreateResolutionResult | ResolutionCreatePersistenceError:
    barrier.wait(timeout=5)
    try:
        return store.create(scoped_command())
    except ResolutionCreatePersistenceError as error:
        return error


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


def test_create_and_supersede_have_only_the_two_serializable_outcomes(
    migrated_database: Engine,
) -> None:
    initial, superseding = _catalogs()
    catalog_store = PostgresRightsCatalogStore(migrated_database)
    assert catalog_store.import_catalog(initial) == CatalogImportResult(2, 0, 0)
    clock = MutableClock(RIGHTS_CHANGE_AT + timedelta(seconds=1))
    create_store = scoped_store(migrated_database, clock=clock)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        create_future = executor.submit(_create_after_barrier, create_store, barrier)
        import_future = executor.submit(
            _import_after_barrier,
            catalog_store,
            superseding,
            barrier,
        )
        create_outcome = create_future.result(timeout=10)
        import_outcome = import_future.result(timeout=10)

    if isinstance(create_outcome, CreateResolutionResult):
        assert create_outcome.disposition is CreateDisposition.CREATED
        assert isinstance(import_outcome, RightsCatalogPersistenceError)
        assert import_outcome.code == "RIGHTS_CATALOG_CONFLICT"
        expected_current = _V1
        assert set(aggregate_counts(migrated_database).values()) == {1}
        with migrated_database.connect() as connection:
            attested = connection.scalar(
                text("SELECT rights_statement_version FROM source_resolution_requests")
            )
        assert attested == _V1
    else:
        assert create_outcome.code == "RIGHTS_STATEMENT_STALE"
        assert import_outcome == CatalogImportResult(1, 1, 1)
        expected_current = _V2
        assert set(aggregate_counts(migrated_database).values()) == {0}

    with migrated_database.connect() as connection:
        current_version = connection.scalar(
            text(
                "SELECT version FROM rights_statement_catalog "
                "WHERE locale='zh-CN' AND superseded_at IS NULL"
            )
        )
    assert current_version == expected_current
