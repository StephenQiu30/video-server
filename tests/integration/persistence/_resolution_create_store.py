"""Deterministic fixtures for the PostgreSQL resolution-create writer."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from sqlalchemy import Engine, text

from tests.integration.persistence._resolution_aggregate import (
    JOB_ID,
    NOW,
    OWNER_ID,
    RESOLUTION_ID,
    RIGHTS_HASH,
    RIGHTS_LOCALE,
    RIGHTS_VERSION,
    seed_rights,
)
from tests.integration.persistence._rights_catalog import insert_statement
from video_server.job.idempotency import ResolutionRequest
from video_server.persistence.resolution_create import (
    CreateResolutionCommand,
    PostgresResolutionCreateStore,
)
from video_server.security.envelope import EncryptedEnvelope, EnvelopeCipher

HMAC_KEY = bytes.fromhex("11" * 32)
KEK = bytes.fromhex("22" * 32)
IDEMPOTENCY_KEY = "resolve-20260718-0001"
URL = "https://media.example/video"
RIGHTS_CHANGE_AT = NOW + timedelta(hours=1)
NEW_RIGHTS_VERSION = "rights-2026-07-19.1"


@dataclass(slots=True)
class MutableClock:
    value: datetime = NOW

    def __call__(self) -> datetime:
        return self.value


def make_request(**changes: object) -> ResolutionRequest:
    request = ResolutionRequest(
        url=URL,
        rights_confirmed=True,
        rights_statement_version=RIGHTS_VERSION,
        rights_statement_locale=RIGHTS_LOCALE,
    )
    return replace(request, **changes)


def make_command(
    *,
    request: ResolutionRequest | None = None,
    key: str = IDEMPOTENCY_KEY,
) -> CreateResolutionCommand:
    return CreateResolutionCommand(
        owner_id=OWNER_ID,
        idempotency_key=key,
        request=request or make_request(),
    )


def make_store(
    engine: Engine,
    *,
    clock: MutableClock | None = None,
) -> PostgresResolutionCreateStore:
    ids = {"job": JOB_ID, "res": RESOLUTION_ID}
    return PostgresResolutionCreateStore(
        engine,
        EnvelopeCipher({"kek-1": KEK}, current_key_id="kek-1"),
        hmac_key=HMAC_KEY,
        clock=clock or MutableClock(),
        id_factory=ids.__getitem__,
    )


def seed_current_rights(engine: Engine) -> None:
    seed_rights(engine)


def supersede_rights(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE rights_statement_catalog
                SET superseded_at=:changed_at
                WHERE version=:version AND locale=:locale
                """
            ),
            {
                "changed_at": RIGHTS_CHANGE_AT,
                "version": RIGHTS_VERSION,
                "locale": RIGHTS_LOCALE,
            },
        )
    insert_statement(
        engine,
        version=NEW_RIGHTS_VERSION,
        effective_at=RIGHTS_CHANGE_AT,
    )


def aggregate_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table: int(connection.scalar(text(f"SELECT count(*) FROM {table}")) or 0)
            for table in (
                "jobs",
                "source_resolution_requests",
                "job_events",
                "outbox_messages",
            )
        }


def request_envelope(engine: Engine) -> EncryptedEnvelope:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT url_ciphertext, url_nonce, url_wrapped_dek,
                       url_wrap_nonce, url_key_id
                FROM source_resolution_requests
                """
            )
        ).one()
    return EncryptedEnvelope(*row)


def decrypt_request_url(engine: Engine) -> bytes:
    aad = f"source_resolution_requests:{RESOLUTION_ID}:{OWNER_ID}:url:v1".encode()
    cipher = EnvelopeCipher({"kek-1": KEK}, current_key_id="kek-1")
    return cipher.decrypt(request_envelope(engine), aad=aad)


def persisted_aggregate_text(engine: Engine) -> str:
    statements = (
        "SELECT j::text FROM jobs AS j",
        "SELECT r::text FROM source_resolution_requests AS r",
        "SELECT e::text FROM job_events AS e",
        "SELECT o::text FROM outbox_messages AS o",
    )
    with engine.connect() as connection:
        return "\n".join(
            str(value)
            for statement in statements
            for value in connection.scalars(text(statement)).all()
        )


@contextmanager
def fail_inserts(engine: Engine, table: str) -> Iterator[None]:
    function = f"test_fail_{table}_insert"
    trigger = f"tr_test_fail_{table}_insert"
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'injected writer failure' USING ERRCODE='XX000';
                END; $$;
                CREATE TRIGGER {trigger} BEFORE INSERT ON {table}
                FOR EACH ROW EXECUTE FUNCTION {function}();
                """
            )
        )
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TRIGGER {trigger} ON {table}"))
            connection.execute(text(f"DROP FUNCTION {function}()"))


def expected_attestation() -> tuple[str, str, str]:
    return RIGHTS_VERSION, RIGHTS_LOCALE, RIGHTS_HASH
