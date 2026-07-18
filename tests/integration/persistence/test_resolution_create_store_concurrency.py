"""Concurrent resolution-create writer contract."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine

from tests.integration.persistence._resolution_create_store import (
    aggregate_counts,
    make_command,
    make_store,
    seed_current_rights,
)
from video_server.persistence.resolution_create import (
    CreateDisposition,
    CreateResolutionResult,
    PostgresResolutionCreateStore,
)

pytestmark = pytest.mark.integration


def _create_after_barrier(
    store: PostgresResolutionCreateStore,
    barrier: Barrier,
) -> CreateResolutionResult:
    barrier.wait(timeout=5)
    return store.create(make_command())


def test_concurrent_same_request_has_one_create_and_one_replay(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    store = make_store(migrated_database)
    barrier = Barrier(2)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: _create_after_barrier(store, barrier), range(2)))

    assert sorted(result.disposition for result in results) == [
        CreateDisposition.CREATED,
        CreateDisposition.REPLAYED,
    ]
    assert len({(result.resolution_id, result.job_id) for result in results}) == 1
    assert set(aggregate_counts(migrated_database).values()) == {1}
