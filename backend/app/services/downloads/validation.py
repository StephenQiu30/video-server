from __future__ import annotations

import re
from datetime import datetime

from app.services.downloads.errors import ApplicationError, ApplicationErrorCode
from app.services.downloads.rules.enums import MediaKind

_OWNER_HASH = re.compile(r"[0-9a-f]{64}")


def media_kind_from_metadata(metadata: dict[str, object]) -> MediaKind:
    value = metadata.get("media_kind", MediaKind.VIDEO.value)
    if not isinstance(value, str):
        raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR)
    try:
        return MediaKind(value)
    except (TypeError, ValueError) as exc:
        raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc


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
