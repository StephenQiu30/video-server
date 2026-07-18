"""Idempotency digest and replay decision boundary."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from enum import StrEnum

from video_server.source.urls import canonicalize_source_url


@dataclass(frozen=True, slots=True)
class ResolutionRequest:
    url: str
    rights_confirmed: bool
    rights_statement_version: str
    rights_statement_locale: str

    def __post_init__(self) -> None:
        if not isinstance(self.url, str) or not self.url:
            raise ValueError("url must be a non-empty string")
        if not isinstance(self.rights_confirmed, bool):
            raise TypeError("rights_confirmed must be a boolean")
        for field_name in ("rights_statement_version", "rights_statement_locale"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be a non-empty string")


class IdempotencyDecision(StrEnum):
    CREATE = "create"
    REPLAY = "replay"
    CONFLICT = "conflict"


def digest_idempotency_key(raw_key: str, *, hmac_key: bytes) -> str:
    _validate_hmac_key(hmac_key)
    if not isinstance(raw_key, str):
        raise TypeError("idempotency key must be a string")
    if not 16 <= len(raw_key) <= 128:
        raise ValueError("idempotency key must contain 16 to 128 characters")
    if any(not 0x21 <= ord(character) <= 0x7E for character in raw_key):
        raise ValueError("idempotency key must contain only visible ASCII without spaces")
    return hmac.new(hmac_key, raw_key.encode("ascii"), hashlib.sha256).hexdigest()


def digest_resolution_request(request: ResolutionRequest, *, hmac_key: bytes) -> str:
    _validate_hmac_key(hmac_key)
    if not isinstance(request, ResolutionRequest):
        raise TypeError("request must be a ResolutionRequest")
    canonical = json.dumps(
        {
            "rights_confirmed": request.rights_confirmed,
            "rights_statement_locale": request.rights_statement_locale,
            "rights_statement_version": request.rights_statement_version,
            "url": canonicalize_source_url(request.url),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hmac.new(hmac_key, canonical, hashlib.sha256).hexdigest()


def resolve_existing(
    stored_request_digest: str | None,
    incoming_request_digest: str,
) -> IdempotencyDecision:
    _validate_digest(incoming_request_digest, field="incoming_request_digest")
    if stored_request_digest is None:
        return IdempotencyDecision.CREATE
    _validate_digest(stored_request_digest, field="stored_request_digest")
    if hmac.compare_digest(stored_request_digest, incoming_request_digest):
        return IdempotencyDecision.REPLAY
    return IdempotencyDecision.CONFLICT


def _validate_hmac_key(value: bytes) -> None:
    if not isinstance(value, bytes):
        raise TypeError("hmac_key must be bytes")
    if len(value) != 32:
        raise ValueError("hmac_key must contain exactly 32 bytes")


def _validate_digest(value: str, *, field: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
