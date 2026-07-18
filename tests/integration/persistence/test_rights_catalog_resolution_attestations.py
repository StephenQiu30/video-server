"""Catalog supersession must preserve durable resolution attestations."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._identity import insert_user
from tests.integration.persistence._resolution_create_store import (
    MutableClock,
    make_command,
    make_store,
)
from tests.integration.persistence._rights_catalog import catalog_entry, make_catalog
from video_server.persistence.resolution_create import CreateDisposition
from video_server.persistence.rights_catalog import (
    CatalogImportResult,
    PostgresRightsCatalogStore,
    RightsCatalogPersistenceError,
)
from video_server.source.rights import RightsCatalog

pytestmark = pytest.mark.integration

_V1 = "rights-2026-07-18.1"
_V2 = "rights-2026-07-18.2"
_CONFIRMED_AT = datetime(2026, 7, 18, 2, tzinfo=UTC)


def _wire_time(hour: int) -> str:
    return datetime(2026, 7, 18, hour, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def _initial_catalog() -> RightsCatalog:
    return make_catalog(
        catalog_entry(version=_V1, locale="en-US"),
        catalog_entry(version=_V1, locale="zh-CN"),
    )


def _superseding_catalog(hour: int) -> RightsCatalog:
    changed_at = _wire_time(hour)
    return make_catalog(
        catalog_entry(version=_V1, locale="en-US", superseded_at=changed_at),
        catalog_entry(version=_V2, locale="en-US", effective_at=changed_at),
        catalog_entry(version=_V1, locale="zh-CN", superseded_at=changed_at),
        catalog_entry(version=_V2, locale="zh-CN", effective_at=changed_at),
    )


def _create_v1_attestation(engine: Engine) -> PostgresRightsCatalogStore:
    catalog_store = PostgresRightsCatalogStore(engine)
    assert catalog_store.import_catalog(_initial_catalog()) == CatalogImportResult(2, 0, 0)
    with engine.begin() as connection:
        insert_user(connection)
    result = make_store(engine, clock=MutableClock(_CONFIRMED_AT)).create(make_command())
    assert result.disposition is CreateDisposition.CREATED
    with engine.connect() as connection:
        confirmed = connection.execute(
            text(
                """
                SELECT rights_statement_version, rights_statement_locale,
                       rights_confirmed_at
                FROM source_resolution_requests
                """
            )
        ).one()
    assert tuple(confirmed) == (_V1, "zh-CN", _CONFIRMED_AT)
    return catalog_store


def _catalog_snapshot(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                text(
                    """
                    SELECT version, locale, statement, statement_sha256,
                           effective_at, expires_at, superseded_at
                    FROM rights_statement_catalog
                    ORDER BY locale, effective_at
                    """
                )
            )
        ]


def _request_snapshot(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                text(
                    """
                    SELECT id, job_id, rights_statement_version,
                           rights_statement_locale, rights_statement_sha256,
                           rights_confirmed_at, created_at
                    FROM source_resolution_requests
                    ORDER BY id
                    """
                )
            )
        ]


@pytest.mark.parametrize("superseded_hour", [1, 2])
def test_catalog_rejects_supersession_not_after_latest_confirmation(
    migrated_database: Engine,
    superseded_hour: int,
) -> None:
    store = _create_v1_attestation(migrated_database)
    catalog_before = _catalog_snapshot(migrated_database)
    request_before = _request_snapshot(migrated_database)

    with pytest.raises(RightsCatalogPersistenceError) as conflict:
        store.import_catalog(_superseding_catalog(superseded_hour))

    assert conflict.value.code == "RIGHTS_CATALOG_CONFLICT"
    assert _catalog_snapshot(migrated_database) == catalog_before
    assert _request_snapshot(migrated_database) == request_before


def test_catalog_allows_supersession_strictly_after_latest_confirmation(
    migrated_database: Engine,
) -> None:
    store = _create_v1_attestation(migrated_database)
    request_before = _request_snapshot(migrated_database)

    assert store.import_catalog(_superseding_catalog(3)) == CatalogImportResult(2, 0, 2)

    assert _request_snapshot(migrated_database) == request_before
    with migrated_database.connect() as connection:
        current = set(
            connection.execute(
                text(
                    "SELECT version, locale FROM rights_statement_catalog "
                    "WHERE superseded_at IS NULL"
                )
            ).all()
        )
    assert current == {(_V2, "en-US"), (_V2, "zh-CN")}
