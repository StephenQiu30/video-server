from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from video_server.job.lease import renew_lease
from video_server.job.outbox import (
    LEASE_DURATION,
    MAX_PUBLISH_ATTEMPTS,
    OutboxState,
    StaleClaim,
    claim,
    mark_publish_failed,
    mark_published,
)

NOW = datetime(2026, 7, 18, tzinfo=UTC)


def test_renewal_and_failure_reject_a_stale_lease_version() -> None:
    claimed = claim(
        OutboxState(),
        claimant="dispatcher-a",
        claim_token="lease-a",
        now=NOW,
    )
    stale_version = claimed.lease_version - 1

    with pytest.raises(StaleClaim, match="version"):
        renew_lease(
            claimed,
            claim_token="lease-a",
            lease_version=stale_version,
            now=NOW + timedelta(seconds=20),
        )
    with pytest.raises(StaleClaim, match="version"):
        mark_publish_failed(
            claimed,
            claim_token="lease-a",
            lease_version=stale_version,
            now=NOW + timedelta(seconds=20),
            retry_delay=timedelta(seconds=1),
        )


def test_expired_lease_cannot_reuse_its_fencing_token() -> None:
    claimed = claim(
        OutboxState(),
        claimant="dispatcher-a",
        claim_token="lease-a",
        now=NOW,
    )

    with pytest.raises(StaleClaim, match="token"):
        claim(
            claimed,
            claimant="dispatcher-b",
            claim_token="lease-a",
            now=NOW + LEASE_DURATION,
        )


def test_tenth_claim_crash_dead_letters_when_lease_expires() -> None:
    claimed = claim(
        OutboxState(attempts=MAX_PUBLISH_ATTEMPTS - 1, lease_version=9),
        claimant="dispatcher-a",
        claim_token="lease-10",
        now=NOW,
    )
    settled = claim(
        claimed,
        claimant="dispatcher-b",
        claim_token="lease-11",
        now=NOW + LEASE_DURATION,
    )

    assert settled.dead_lettered_at == NOW + LEASE_DURATION
    assert settled.terminal_error_code == "QUEUE_DELIVERY_FAILED"
    assert settled.claim_token is None
    assert settled.lease_version == MAX_PUBLISH_ATTEMPTS


def test_historical_token_cannot_complete_a_later_lease_version() -> None:
    first = claim(
        OutboxState(),
        claimant="dispatcher-a",
        claim_token="token-x",
        now=NOW,
    )
    second = claim(
        first,
        claimant="dispatcher-b",
        claim_token="token-y",
        now=NOW + LEASE_DURATION,
    )
    released = mark_publish_failed(
        second,
        claim_token="token-y",
        lease_version=second.lease_version,
        now=NOW + LEASE_DURATION + timedelta(seconds=1),
        retry_delay=timedelta(seconds=1),
    )
    third = claim(
        released,
        claimant="dispatcher-c",
        claim_token="token-x",
        now=NOW + LEASE_DURATION + timedelta(seconds=2),
    )

    assert (first.lease_version, second.lease_version, third.lease_version) == (1, 2, 3)
    assert released.lease_version == second.lease_version
    with pytest.raises(StaleClaim, match="version"):
        mark_published(
            third,
            claim_token="token-x",
            lease_version=first.lease_version,
            now=NOW + LEASE_DURATION + timedelta(seconds=3),
        )

    published = mark_published(
        third,
        claim_token="token-x",
        lease_version=third.lease_version,
        now=NOW + LEASE_DURATION + timedelta(seconds=3),
    )
    assert published.lease_version == third.lease_version
    assert published.published_at == NOW + LEASE_DURATION + timedelta(seconds=3)
