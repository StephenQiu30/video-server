"""Outbox lease-renewal boundary."""

from __future__ import annotations

from datetime import datetime, timedelta

from video_server.job.outbox import OutboxState

LEASE_RENEWAL_INTERVAL = timedelta(seconds=20)


def renew_lease(
    state: OutboxState,
    *,
    claim_token: str,
    now: datetime,
) -> OutboxState:
    """Extend the current fenced lease without consuming an attempt."""

    raise NotImplementedError("outbox lease renewal is not implemented")
