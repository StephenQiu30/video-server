"""Internal transaction operations for source-resolution creation."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection

from video_server.persistence._advisory_locks import (
    SUPPORTED_RIGHTS_LOCALES,
    lock_resolution_idempotency,
    lock_rights_locales,
)
from video_server.persistence._resolution_create_sql import (
    INSERT_EVENT,
    INSERT_JOB,
    INSERT_OUTBOX,
    INSERT_REQUEST,
    SELECT_CURRENT_RIGHTS,
    SELECT_EXISTING,
)
from video_server.security.envelope import EnvelopeCipher

IdFactory = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class PreparedResolutionCreate:
    owner_id: str
    idempotency_key_digest: str
    request_digest: str
    canonical_url: str
    rights_confirmed: bool
    rights_statement_version: str
    rights_statement_locale: str


@dataclass(frozen=True, slots=True)
class PersistedResolutionCreate:
    replayed: bool
    resolution_id: str
    job_id: str
    created_at: datetime


class CreateRejectedSignal(Exception):
    """Expected domain rejection that must roll back the transaction."""

    def __init__(self, code: str) -> None:
        self.code = code


class UnsafeTransactionSignal(Exception):
    """The DBAPI connection cannot guarantee an atomic aggregate write."""


def create_resolution(
    connection: Connection,
    prepared: PreparedResolutionCreate,
    *,
    cipher: EnvelopeCipher,
    clock: Callable[[], datetime],
    id_factory: IdFactory,
) -> PersistedResolutionCreate:
    _ensure_transactional(connection)
    lock_resolution_idempotency(
        connection,
        owner_id=prepared.owner_id,
        operation="probe",
        key_digest=prepared.idempotency_key_digest,
    )
    existing = (
        connection.execute(
            SELECT_EXISTING,
            {
                "owner_id": prepared.owner_id,
                "idempotency_key_digest": prepared.idempotency_key_digest,
            },
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        if hmac.compare_digest(existing["request_digest"], prepared.request_digest):
            return PersistedResolutionCreate(
                True,
                existing["id"],
                existing["job_id"],
                _validated_now(existing["created_at"]),
            )
        raise CreateRejectedSignal("IDEMPOTENCY_CONFLICT")

    if not prepared.rights_confirmed:
        raise CreateRejectedSignal("RIGHTS_CONFIRMATION_REQUIRED")
    if prepared.rights_statement_locale not in SUPPORTED_RIGHTS_LOCALES:
        raise CreateRejectedSignal("RIGHTS_STATEMENT_STALE")

    lock_rights_locales(connection, (prepared.rights_statement_locale,))
    created_at = _validated_now(clock())
    rights = (
        connection.execute(
            SELECT_CURRENT_RIGHTS,
            {
                "rights_statement_locale": prepared.rights_statement_locale,
                "created_at": created_at,
            },
        )
        .mappings()
        .all()
    )
    if len(rights) != 1:
        raise CreateRejectedSignal("RIGHTS_STATEMENT_UNAVAILABLE")
    current = rights[0]
    if current["version"] != prepared.rights_statement_version:
        raise CreateRejectedSignal("RIGHTS_STATEMENT_STALE")

    resolution_id = id_factory("res")
    job_id = id_factory("job")
    aad = f"source_resolution_requests:{resolution_id}:{prepared.owner_id}:url:v1".encode()
    envelope = cipher.encrypt(prepared.canonical_url.encode(), aad=aad)
    values: dict[str, object] = {
        "resolution_id": resolution_id,
        "job_id": job_id,
        "owner_id": prepared.owner_id,
        "idempotency_key_digest": prepared.idempotency_key_digest,
        "request_digest": prepared.request_digest,
        "url_ciphertext": envelope.ciphertext,
        "url_nonce": envelope.nonce,
        "url_wrapped_dek": envelope.wrapped_dek,
        "url_wrap_nonce": envelope.wrap_nonce,
        "url_key_id": envelope.key_id,
        "rights_statement_version": current["version"],
        "rights_statement_locale": current["locale"],
        "rights_statement_sha256": current["statement_sha256"],
        "created_at": created_at,
        "detail_eligible_at": created_at + timedelta(hours=166),
        "detail_must_purge_by": created_at + timedelta(hours=168),
    }
    for statement in (INSERT_JOB, INSERT_REQUEST, INSERT_EVENT, INSERT_OUTBOX):
        connection.execute(statement, values)
    return PersistedResolutionCreate(False, resolution_id, job_id, created_at)


def _ensure_transactional(connection: Connection) -> None:
    driver_connection = connection.connection.driver_connection
    if getattr(driver_connection, "autocommit", None) is not False:
        raise UnsafeTransactionSignal


def _validated_now(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return value.astimezone(UTC)
