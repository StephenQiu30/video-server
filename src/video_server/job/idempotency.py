"""Idempotency digest and replay decision boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class ResolutionRequest:
    url: str
    rights_confirmed: bool
    rights_statement_version: str
    rights_statement_locale: str


class IdempotencyDecision(StrEnum):
    CREATE = "create"
    REPLAY = "replay"
    CONFLICT = "conflict"


def digest_idempotency_key(raw_key: str, *, hmac_key: bytes) -> str:
    raise NotImplementedError("idempotency key digest is not implemented")


def digest_resolution_request(request: ResolutionRequest, *, hmac_key: bytes) -> str:
    raise NotImplementedError("resolution request digest is not implemented")


def resolve_existing(
    stored_request_digest: str | None,
    incoming_request_digest: str,
) -> IdempotencyDecision:
    raise NotImplementedError("idempotency replay resolution is not implemented")
