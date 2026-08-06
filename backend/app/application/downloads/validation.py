from __future__ import annotations

import re
from datetime import datetime

from app.application.downloads.errors import (
    ApplicationError,
    ApplicationErrorCode,
)

_OWNER_HASH = re.compile(r"[0-9a-f]{64}")


def validate_owner_hash(owner_hash: str) -> str:
    if _OWNER_HASH.fullmatch(owner_hash) is None:
        raise ApplicationError(ApplicationErrorCode.INVALID_REQUEST)
    return owner_hash


def validate_idempotency_key(value: str) -> str:
    if not value or len(value) > 128 or value != value.strip():
        raise ApplicationError(ApplicationErrorCode.INVALID_REQUEST)
    return value


def validate_now(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return timezone-aware datetime")
    return value
