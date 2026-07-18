"""Private validation and fencing rules for outbox leases."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from video_server.errors import DomainError

if TYPE_CHECKING:
    from video_server.job.outbox import OutboxState


class LeaseUnavailable(DomainError):
    """An outbox row cannot be claimed at this time."""


class StaleClaim(DomainError):
    """A compare-and-set lease no longer owns the row."""


def aware(value: datetime, *, field: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include timezone information")


def lease_unavailable(detail: str, *, retryable: bool = False) -> LeaseUnavailable:
    return LeaseUnavailable("OUTBOX_LEASE_UNAVAILABLE", detail, retryable=retryable)


def stale_claim(detail: str) -> StaleClaim:
    return StaleClaim("OUTBOX_STALE_CLAIM", detail)


def absolute(value: datetime) -> datetime:
    return value.astimezone(UTC)


def validate_operation_time(state: OutboxState, *, now: datetime) -> None:
    aware(now, field="now")
    if state.claimed_at is not None and absolute(now) < absolute(state.claimed_at):
        raise ValueError("operation time cannot precede claim time")


def require_owner(
    state: OutboxState,
    *,
    claim_token: str,
    lease_version: int,
    now: datetime,
) -> None:
    if not isinstance(claim_token, str) or not claim_token:
        raise ValueError("claim token must be a non-empty string")
    if isinstance(lease_version, bool) or not isinstance(lease_version, int):
        raise TypeError("lease version must be an integer")
    if lease_version < 0:
        raise ValueError("lease version cannot be negative")
    if state.claim_token != claim_token:
        raise stale_claim("claim token no longer owns the outbox row")
    if state.lease_version != lease_version:
        raise stale_claim("lease version no longer owns the outbox row")
    validate_operation_time(state, now=now)
    if state.lease_expires_at is None or absolute(now) >= absolute(state.lease_expires_at):
        raise stale_claim("claim token lease has expired")
