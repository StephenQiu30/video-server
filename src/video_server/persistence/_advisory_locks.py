"""Stable PostgreSQL transaction advisory-lock domains."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import Connection, text

SUPPORTED_RIGHTS_LOCALES = ("en-US", "zh-CN")

_LOCK = text("SELECT pg_advisory_xact_lock(:lock_key)")


def lock_rights_locales(connection: Connection, locales: Iterable[str]) -> None:
    requested = set(locales)
    if not requested or not requested <= set(SUPPORTED_RIGHTS_LOCALES):
        raise ValueError("rights lock locales must be a non-empty supported subset")
    for locale in SUPPORTED_RIGHTS_LOCALES:
        if locale in requested:
            connection.execute(_LOCK, {"lock_key": rights_locale_lock_key(locale)})


def lock_resolution_idempotency(
    connection: Connection,
    *,
    owner_id: UUID,
    operation: str,
    key_digest: str,
) -> None:
    connection.execute(
        _LOCK,
        {
            "lock_key": _framed_lock_key(
                "resolution-idempotency",
                str(owner_id),
                operation,
                key_digest,
            )
        },
    )


def rights_locale_lock_key(locale: str) -> int:
    if locale not in SUPPORTED_RIGHTS_LOCALES:
        raise ValueError("unsupported rights locale lock")
    digest = hashlib.sha256(f"video-server:rights-catalog:{locale}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _framed_lock_key(namespace: str, *parts: str) -> int:
    payload = bytearray(b"video-server:lock:v1")
    for part in (namespace, *parts):
        encoded = part.encode("utf-8")
        payload.extend(len(encoded).to_bytes(8, "big"))
        payload.extend(encoded)
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=True)
