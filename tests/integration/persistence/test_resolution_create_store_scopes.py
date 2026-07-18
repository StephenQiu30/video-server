"""Digest, owner-scope, and conflicting-race writer contract."""

from __future__ import annotations

import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._resolution_create_scopes import (
    KEY_A,
    KEY_B,
    OWNER_A,
    OWNER_B,
    URL_A,
    URL_B,
    SequentialIdFactory,
    scoped_command,
    scoped_request,
    scoped_store,
)
from tests.integration.persistence._resolution_create_store import (
    HMAC_KEY,
    aggregate_counts,
    seed_current_rights,
)
from video_server.job.idempotency import ResolutionRequest, digest_resolution_request
from video_server.persistence.resolution_create import (
    CreateDisposition,
    CreateResolutionResult,
    PostgresResolutionCreateStore,
    ResolutionCreatePersistenceError,
)

pytestmark = pytest.mark.integration


def _run_conflicting_create(
    store: PostgresResolutionCreateStore,
    barrier: Barrier,
    label: str,
    request: ResolutionRequest,
) -> tuple[str, CreateResolutionResult | ResolutionCreatePersistenceError]:
    barrier.wait(timeout=5)
    try:
        return label, store.create(scoped_command(request=request))
    except ResolutionCreatePersistenceError as error:
        return label, error


def test_concurrent_same_key_different_payload_has_one_durable_winner(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    store = scoped_store(migrated_database)
    barrier = Barrier(2)
    requests = {"a": scoped_request(url=URL_A), "b": scoped_request(url=URL_B)}

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                lambda item: _run_conflicting_create(store, barrier, item[0], item[1]),
                requests.items(),
            )
        )

    winners = [
        (label, value) for label, value in outcomes if isinstance(value, CreateResolutionResult)
    ]
    losers = [value for _, value in outcomes if isinstance(value, ResolutionCreatePersistenceError)]
    assert len(winners) == len(losers) == 1
    assert winners[0][1].disposition is CreateDisposition.CREATED
    assert losers[0].code == "IDEMPOTENCY_CONFLICT"
    with migrated_database.connect() as connection:
        stored_digest = connection.scalar(
            text("SELECT request_digest FROM source_resolution_requests")
        )
    assert stored_digest == digest_resolution_request(requests[winners[0][0]], hmac_key=HMAC_KEY)
    assert set(aggregate_counts(migrated_database).values()) == {1}


def test_writer_persists_exact_hmac_key_and_canonical_request_digests(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    request = scoped_request()
    scoped_store(migrated_database).create(scoped_command(request=request))
    canonical = json.dumps(
        {
            "rights_confirmed": True,
            "rights_statement_locale": "zh-CN",
            "rights_statement_version": "rights-2026-07-18.1",
            "url": URL_A,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    expected = (
        hmac.new(HMAC_KEY, KEY_A.encode(), hashlib.sha256).hexdigest(),
        hmac.new(HMAC_KEY, canonical, hashlib.sha256).hexdigest(),
    )
    with migrated_database.connect() as connection:
        stored = connection.execute(
            text("SELECT idempotency_key_digest, request_digest FROM source_resolution_requests")
        ).one()
    assert tuple(stored) == expected


def test_same_request_with_different_keys_creates_two_aggregates(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    store = scoped_store(migrated_database)

    results = [store.create(scoped_command(key=key)) for key in (KEY_A, KEY_B)]

    assert [result.disposition for result in results] == [
        CreateDisposition.CREATED,
        CreateDisposition.CREATED,
    ]
    with migrated_database.connect() as connection:
        rows = connection.execute(
            text("SELECT idempotency_key_digest, request_digest FROM source_resolution_requests")
        ).all()
    assert len({row.idempotency_key_digest for row in rows}) == 2
    assert len({row.request_digest for row in rows}) == 1
    assert set(aggregate_counts(migrated_database).values()) == {2}


def test_same_key_is_independent_between_owner_scopes(migrated_database: Engine) -> None:
    seed_current_rights(migrated_database)
    store = scoped_store(migrated_database, factory=SequentialIdFactory())

    results = [store.create(scoped_command(owner_id=owner)) for owner in (OWNER_A, OWNER_B)]

    assert all(result.disposition is CreateDisposition.CREATED for result in results)
    with migrated_database.connect() as connection:
        owners = set(connection.scalars(text("SELECT owner_id FROM source_resolution_requests")))
    assert owners == {OWNER_A, OWNER_B}
    assert set(aggregate_counts(migrated_database).values()) == {2}
