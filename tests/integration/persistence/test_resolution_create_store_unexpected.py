"""Unexpected-failure and UTC replay contract for resolution creation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
from sqlalchemy import Engine, create_engine, text

from tests.integration.persistence._resolution_aggregate import JOB_ID, RESOLUTION_ID
from tests.integration.persistence._resolution_create_store import (
    HMAC_KEY,
    KEK,
    MutableClock,
    aggregate_counts,
    make_command,
    make_request,
    make_store,
    seed_current_rights,
)
from video_server.persistence.resolution_create import (
    PostgresResolutionCreateStore,
    ResolutionCreatePersistenceError,
)
from video_server.security.envelope import EncryptedEnvelope, EnvelopeCipher
from video_server.source.urls import SourceURLValidationError

pytestmark = pytest.mark.integration

_ID_SECRET = "id-factory-secret-token"
_CIPHER_SECRET = "cipher-secret-key-material"


class _ExplodingCipher(EnvelopeCipher):
    def encrypt(self, plaintext: bytes, *, aad: bytes) -> EncryptedEnvelope:
        raise RuntimeError(_CIPHER_SECRET)


def _fixed_id(kind: str) -> str:
    return {"job": JOB_ID, "res": RESOLUTION_ID}[kind]


def _exploding_id(_: str) -> str:
    raise RuntimeError(_ID_SECRET)


def _injected_store(
    engine: Engine,
    *,
    cipher: EnvelopeCipher,
    id_factory: Callable[[str], str],
) -> PostgresResolutionCreateStore:
    return PostgresResolutionCreateStore(
        engine,
        cipher,
        hmac_key=HMAC_KEY,
        clock=MutableClock(),
        id_factory=id_factory,
    )


@pytest.mark.parametrize(
    ("cipher", "id_factory", "secret"),
    [
        (EnvelopeCipher({"kek-1": KEK}, current_key_id="kek-1"), _exploding_id, _ID_SECRET),
        (_ExplodingCipher({"kek-1": KEK}, current_key_id="kek-1"), _fixed_id, _CIPHER_SECRET),
    ],
)
def test_unexpected_transaction_dependency_failure_is_safe_and_atomic(
    migrated_database: Engine,
    cipher: EnvelopeCipher,
    id_factory: Callable[[str], str],
    secret: str,
) -> None:
    seed_current_rights(migrated_database)

    with pytest.raises(ResolutionCreatePersistenceError) as failed:
        _injected_store(
            migrated_database,
            cipher=cipher,
            id_factory=id_factory,
        ).create(make_command())

    assert failed.value.code == "INTERNAL_ERROR"
    assert secret not in str(failed.value)
    assert set(aggregate_counts(migrated_database).values()) == {0}


def test_prepare_source_url_validation_error_is_not_hidden(migrated_database: Engine) -> None:
    request = make_request(url="http://media.example/video")

    with pytest.raises(SourceURLValidationError) as invalid:
        make_store(migrated_database).create(make_command(request=request))

    assert invalid.value.code == "INVALID_URL"
    assert set(aggregate_counts(migrated_database).values()) == {0}


def test_replay_created_at_is_normalized_to_utc_under_non_utc_session(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    timezone_engine = create_engine(
        migrated_database.url,
        connect_args={"options": "-c timezone=Asia/Shanghai"},
    )
    try:
        with timezone_engine.connect() as connection:
            assert connection.scalar(text("SHOW TIME ZONE")) == "Asia/Shanghai"
        store = make_store(timezone_engine)
        created = store.create(make_command())
        replayed = store.create(make_command())
    finally:
        timezone_engine.dispose()

    assert created.created_at.utcoffset() == timedelta(0)
    assert replayed.created_at.utcoffset() == timedelta(0)
    assert replayed.created_at == created.created_at
