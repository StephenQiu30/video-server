"""Outbox lease-renewal boundary."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from video_server.job._outbox_rules import require_owner as _require_owner
from video_server.job.outbox import LEASE_DURATION, OutboxState

LEASE_RENEWAL_INTERVAL = timedelta(seconds=20)


def renew_lease(
    state: OutboxState,
    *,
    claim_token: str,
    lease_version: int,
    now: datetime,
) -> OutboxState:
    """Extend the current fenced lease without consuming an attempt."""

    if not isinstance(state, OutboxState):
        raise TypeError("state must be an OutboxState")
    _require_owner(state, claim_token=claim_token, lease_version=lease_version, now=now)
    return replace(state, lease_expires_at=now + LEASE_DURATION)
