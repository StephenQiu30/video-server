from __future__ import annotations

import re
from datetime import datetime

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
)

_OWNER_HASH = re.compile(r"[0-9a-f]{64}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
MAX_CUSTOM_PROMPT_LENGTH = 4_000


def validate_owner_hash(value: str) -> str:
    if _OWNER_HASH.fullmatch(value) is None:
        _invalid()
    return value


def validate_idempotency_key(value: str) -> str:
    if not value or len(value) > 128 or value != value.strip():
        _invalid()
    return value


def validate_label(value: str, *, maximum: int) -> str:
    if not value or value != value.strip() or len(value) > maximum:
        _invalid()
    return value


def validate_custom_prompt(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if "\x00" in normalized or len(normalized) > MAX_CUSTOM_PROMPT_LENGTH:
        _invalid()
    return normalized


def validate_sha256(value: str) -> str:
    if _SHA256.fullmatch(value) is None:
        raise AnalysisApplicationError(AnalysisApplicationErrorCode.INTERNAL_ERROR)
    return value


def validate_now(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return timezone-aware datetime")
    return value


def _invalid() -> None:
    raise AnalysisApplicationError(AnalysisApplicationErrorCode.INVALID_REQUEST)
