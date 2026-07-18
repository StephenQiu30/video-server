"""Pure transactional-outbox lease state boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from video_server.errors import DomainError

LEASE_DURATION = timedelta(seconds=60)
MAX_PUBLISH_ATTEMPTS = 10


class LeaseUnavailable(DomainError):
    """An outbox row cannot be claimed at this time."""


class StaleClaim(DomainError):
    """A compare-and-set claim token no longer owns the row."""


@dataclass(frozen=True, slots=True)
class OutboxState:
    claimed_by: str | None = None
    claim_token: str | None = None
    claimed_at: datetime | None = None
    lease_expires_at: datetime | None = None
    attempts: int = 0
    next_attempt_at: datetime | None = None
    published_at: datetime | None = None
    dead_lettered_at: datetime | None = None
    terminal_error_code: str | None = None


def claim(
    state: OutboxState,
    *,
    claimant: str,
    claim_token: str,
    now: datetime,
) -> OutboxState:
    raise NotImplementedError("outbox claim is not implemented")


def mark_published(
    state: OutboxState,
    *,
    claim_token: str,
    now: datetime,
) -> OutboxState:
    raise NotImplementedError("outbox publish completion is not implemented")


def mark_publish_failed(
    state: OutboxState,
    *,
    claim_token: str,
    now: datetime,
    retry_delay: timedelta,
) -> OutboxState:
    raise NotImplementedError("outbox publish failure is not implemented")
