"""Pure transactional-outbox lease state boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from video_server.job._outbox_rules import (
    LeaseUnavailable as LeaseUnavailable,
)
from video_server.job._outbox_rules import (
    StaleClaim as StaleClaim,
)
from video_server.job._outbox_rules import (
    absolute as _absolute,
)
from video_server.job._outbox_rules import (
    aware as _aware,
)
from video_server.job._outbox_rules import (
    lease_unavailable as _lease_unavailable,
)
from video_server.job._outbox_rules import (
    require_owner as _require_owner,
)
from video_server.job._outbox_rules import (
    stale_claim as _stale_claim,
)
from video_server.job._outbox_rules import (
    validate_operation_time as _validate_operation_time,
)

LEASE_DURATION = timedelta(seconds=60)
MAX_PUBLISH_ATTEMPTS = 10


@dataclass(frozen=True, slots=True)
class OutboxState:
    claimed_by: str | None = None
    claim_token: str | None = None
    claimed_at: datetime | None = None
    lease_expires_at: datetime | None = None
    attempts: int = 0
    lease_version: int = 0
    next_attempt_at: datetime | None = None
    published_at: datetime | None = None
    dead_lettered_at: datetime | None = None
    terminal_error_code: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int):
            raise TypeError("attempts must be an integer")
        if not 0 <= self.attempts <= MAX_PUBLISH_ATTEMPTS:
            raise ValueError("attempts must be between zero and the publish limit")
        if isinstance(self.lease_version, bool) or not isinstance(self.lease_version, int):
            raise TypeError("lease_version must be an integer")
        if self.lease_version < 0:
            raise ValueError("lease_version cannot be negative")
        for field, value in (
            ("claimed_at", self.claimed_at),
            ("lease_expires_at", self.lease_expires_at),
            ("next_attempt_at", self.next_attempt_at),
            ("published_at", self.published_at),
            ("dead_lettered_at", self.dead_lettered_at),
        ):
            if value is not None:
                _aware(value, field=field)
        lease_parts = (
            self.claimed_by,
            self.claim_token,
            self.claimed_at,
            self.lease_expires_at,
        )
        if any(value is None for value in lease_parts) != all(
            value is None for value in lease_parts
        ):
            raise ValueError("lease ownership fields must be set or cleared together")
        if self.attempts == 0 and any(
            value is not None for value in (*lease_parts, self.next_attempt_at, self.published_at)
        ):
            raise ValueError("active, retry, and published states require a consumed attempt")
        if self.lease_version == 0 and any(
            value is not None for value in (*lease_parts, self.next_attempt_at, self.published_at)
        ):
            raise ValueError("leased lifecycle states require a positive lease_version")
        if (
            self.claimed_at is not None
            and self.lease_expires_at is not None
            and self.lease_expires_at <= self.claimed_at
        ):
            raise ValueError("lease expiry must follow claim time")
        if self.published_at is not None and self.dead_lettered_at is not None:
            raise ValueError("published and dead-letter states are mutually exclusive")
        if self.dead_lettered_at is None and self.terminal_error_code is not None:
            raise ValueError("terminal error requires a dead-letter timestamp")
        if self.dead_lettered_at is not None:
            if self.terminal_error_code != "QUEUE_DELIVERY_FAILED":
                raise ValueError("dead-letter state requires QUEUE_DELIVERY_FAILED")
            if self.attempts != MAX_PUBLISH_ATTEMPTS:
                raise ValueError("dead-letter state requires exhausted attempts")
        if (self.published_at is not None or self.dead_lettered_at is not None) and any(
            value is not None for value in (*lease_parts, self.next_attempt_at)
        ):
            raise ValueError("terminal outbox states cannot retain a lease or retry time")


def _dead_letter(state: OutboxState, *, now: datetime) -> OutboxState:
    return replace(
        state,
        claimed_by=None,
        claim_token=None,
        claimed_at=None,
        lease_expires_at=None,
        next_attempt_at=None,
        dead_lettered_at=now,
        terminal_error_code="QUEUE_DELIVERY_FAILED",
    )


def claim(
    state: OutboxState,
    *,
    claimant: str,
    claim_token: str,
    now: datetime,
) -> OutboxState:
    _aware(now, field="now")
    if not isinstance(claimant, str) or not claimant:
        raise ValueError("claimant must be a non-empty string")
    if not isinstance(claim_token, str) or not claim_token:
        raise ValueError("claim token must be a non-empty string")
    if state.published_at is not None:
        raise _lease_unavailable("published outbox rows cannot be claimed")
    if state.dead_lettered_at is not None:
        raise _lease_unavailable("dead-letter outbox rows cannot be claimed")
    _validate_operation_time(state, now=now)
    if state.claim_token == claim_token:
        raise _stale_claim("claim token cannot be reused as a fencing token")
    if state.next_attempt_at is not None and _absolute(now) < _absolute(state.next_attempt_at):
        raise _lease_unavailable("retry delay has not elapsed", retryable=True)
    if state.lease_expires_at is not None and _absolute(now) < _absolute(state.lease_expires_at):
        raise _lease_unavailable("an active lease already owns the outbox row", retryable=True)
    if state.attempts >= MAX_PUBLISH_ATTEMPTS:
        return _dead_letter(state, now=now)
    return replace(
        state,
        claimed_by=claimant,
        claim_token=claim_token,
        claimed_at=now,
        lease_expires_at=now + LEASE_DURATION,
        attempts=state.attempts + 1,
        lease_version=state.lease_version + 1,
        next_attempt_at=None,
    )


def mark_published(
    state: OutboxState,
    *,
    claim_token: str,
    lease_version: int,
    now: datetime,
) -> OutboxState:
    _require_owner(state, claim_token=claim_token, lease_version=lease_version, now=now)
    return replace(
        state,
        claimed_by=None,
        claim_token=None,
        claimed_at=None,
        lease_expires_at=None,
        next_attempt_at=None,
        published_at=now,
    )


def mark_publish_failed(
    state: OutboxState,
    *,
    claim_token: str,
    lease_version: int,
    now: datetime,
    retry_delay: timedelta,
) -> OutboxState:
    if not isinstance(retry_delay, timedelta):
        raise TypeError("retry delay must be a timedelta")
    if not timedelta(seconds=1) <= retry_delay <= timedelta(seconds=30):
        raise ValueError("retry delay must be between one and 30 seconds")
    _require_owner(state, claim_token=claim_token, lease_version=lease_version, now=now)

    released = replace(
        state,
        claimed_by=None,
        claim_token=None,
        claimed_at=None,
        lease_expires_at=None,
    )
    if state.attempts >= MAX_PUBLISH_ATTEMPTS:
        return _dead_letter(released, now=now)
    return replace(released, next_attempt_at=now + retry_delay)
