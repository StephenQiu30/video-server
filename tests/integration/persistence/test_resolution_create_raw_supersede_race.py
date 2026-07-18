"""A raw catalog update cannot race a durable resolution attestation."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from queue import Queue
from threading import Event
from time import monotonic

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._resolution_aggregate import JOB_ID, NOW, RESOLUTION_ID
from tests.integration.persistence._resolution_create_store import (
    HMAC_KEY,
    KEK,
    MutableClock,
    make_command,
    seed_current_rights,
)
from tests.integration.persistence._rights_catalog import assert_constraint
from video_server.persistence.resolution_create import (
    CreateDisposition,
    CreateResolutionResult,
    PostgresResolutionCreateStore,
)
from video_server.security.envelope import EnvelopeCipher

pytestmark = pytest.mark.integration

_CONSTRAINT = "ck_rights_statement_catalog_supersede_after_attestation"
_CONFIRMED_AT = NOW + timedelta(hours=2)


class _BlockingIdFactory:
    def __init__(self) -> None:
        self.rights_selected = Event()
        self.release = Event()
        self._blocked = False

    def __call__(self, kind: str) -> str:
        if not self._blocked:
            self._blocked = True
            self.rights_selected.set()
            if not self.release.wait(timeout=5):
                raise AssertionError("writer was not released after selecting rights")
        return {"res": RESOLUTION_ID, "job": JOB_ID}[kind]


def _make_blocked_store(
    engine: Engine,
    ids: _BlockingIdFactory,
) -> PostgresResolutionCreateStore:
    return PostgresResolutionCreateStore(
        engine,
        EnvelopeCipher({"kek-1": KEK}, current_key_id="kek-1"),
        hmac_key=HMAC_KEY,
        clock=MutableClock(_CONFIRMED_AT),
        id_factory=ids,
    )


def _raw_retroactive_update(engine: Engine, backend: Queue[int]) -> IntegrityError | None:
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL lock_timeout='5s'"))
            backend.put(int(connection.scalar(text("SELECT pg_backend_pid()"))))
            connection.execute(
                text(
                    """
                    UPDATE rights_statement_catalog
                    SET superseded_at=:confirmed_at
                    WHERE version='rights-2026-07-18.1' AND locale='zh-CN'
                    """
                ),
                {"confirmed_at": _CONFIRMED_AT},
            )
    except IntegrityError as error:
        return error
    return None


def _await_lock_wait(
    engine: Engine,
    backend_pid: int,
    update: Future[IntegrityError | None],
) -> None:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        if update.done():
            pytest.fail("raw UPDATE did not wait for the writer's rights row lock")
        with engine.connect() as connection:
            wait_type = connection.scalar(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": backend_pid},
            )
        if wait_type == "Lock":
            return
        Event().wait(0.01)
    pytest.fail("raw UPDATE never reached a PostgreSQL lock wait")


def test_writer_share_lock_serializes_raw_retroactive_supersession(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    ids = _BlockingIdFactory()
    store = _make_blocked_store(migrated_database, ids)
    backend: Queue[int] = Queue(maxsize=1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        created = executor.submit(store.create, make_command())
        assert ids.rights_selected.wait(timeout=5)
        update = executor.submit(_raw_retroactive_update, migrated_database, backend)
        try:
            _await_lock_wait(migrated_database, backend.get(timeout=5), update)
        finally:
            ids.release.set()
        result: CreateResolutionResult = created.result(timeout=5)
        rejected = update.result(timeout=5)

    assert result.disposition is CreateDisposition.CREATED
    assert isinstance(rejected, IntegrityError)
    assert_constraint(rejected, name=_CONSTRAINT)
    with migrated_database.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT superseded_at FROM rights_statement_catalog "
                    "WHERE version='rights-2026-07-18.1' AND locale='zh-CN'"
                )
            )
            is None
        )
        assert connection.scalar(text("SELECT count(*) FROM source_resolution_requests")) == 1
