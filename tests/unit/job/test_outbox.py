from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from video_server.job.outbox import (
    LEASE_DURATION,
    MAX_PUBLISH_ATTEMPTS,
    LeaseUnavailable,
    OutboxState,
    StaleClaim,
    claim,
    mark_publish_failed,
    mark_published,
)

NOW = datetime(2026, 7, 18, 0, 0, tzinfo=UTC)


def test_claim_uses_a_fixed_60_second_lease() -> None:
    initial = OutboxState()
    assert initial.lease_version == 0
    claimed = claim(
        initial,
        claimant="dispatcher-a",
        claim_token="lease-a",
        now=NOW,
    )

    assert timedelta(seconds=60) == LEASE_DURATION
    assert claimed.claimed_by == "dispatcher-a"
    assert claimed.claim_token == "lease-a"
    assert claimed.lease_expires_at == NOW + timedelta(seconds=60)
    assert claimed.attempts == 1
    assert claimed.lease_version == 1


def test_active_lease_cannot_be_claimed_by_another_dispatcher() -> None:
    claimed = claim(
        OutboxState(),
        claimant="dispatcher-a",
        claim_token="lease-a",
        now=NOW,
    )

    with pytest.raises(LeaseUnavailable, match="lease"):
        claim(
            claimed,
            claimant="dispatcher-b",
            claim_token="lease-b",
            now=NOW + timedelta(seconds=59),
        )


def test_expired_lease_is_reclaimed_with_a_new_cas_token() -> None:
    original = claim(
        OutboxState(),
        claimant="dispatcher-a",
        claim_token="lease-a",
        now=NOW,
    )
    reclaimed = claim(
        original,
        claimant="dispatcher-b",
        claim_token="lease-b",
        now=NOW + timedelta(seconds=60),
    )

    assert reclaimed.claimed_by == "dispatcher-b"
    assert reclaimed.claim_token == "lease-b"
    assert reclaimed.lease_expires_at == NOW + timedelta(seconds=120)
    assert reclaimed.attempts == 2
    assert reclaimed.lease_version == 2

    with pytest.raises(StaleClaim, match="token"):
        mark_published(
            reclaimed,
            claim_token="lease-a",
            lease_version=original.lease_version,
            now=NOW + timedelta(seconds=61),
        )

    published = mark_published(
        reclaimed,
        claim_token="lease-b",
        lease_version=reclaimed.lease_version,
        now=NOW + timedelta(seconds=61),
    )
    assert published.published_at == NOW + timedelta(seconds=61)


def test_first_nine_failures_remain_retryable_and_tenth_dead_letters() -> None:
    state = OutboxState()
    now = NOW

    for attempt in range(1, MAX_PUBLISH_ATTEMPTS + 1):
        token = f"lease-{attempt}"
        state = claim(
            state,
            claimant="dispatcher-a",
            claim_token=token,
            now=now,
        )
        state = mark_publish_failed(
            state,
            claim_token=token,
            lease_version=state.lease_version,
            now=now,
            retry_delay=timedelta(seconds=1),
        )

        assert state.attempts == attempt
        assert state.lease_version == attempt
        if attempt < MAX_PUBLISH_ATTEMPTS:
            assert state.dead_lettered_at is None
            assert state.terminal_error_code is None
            assert state.next_attempt_at == now + timedelta(seconds=1)
            now = state.next_attempt_at

    assert MAX_PUBLISH_ATTEMPTS == 10
    assert state.dead_lettered_at == now
    assert state.terminal_error_code == "QUEUE_DELIVERY_FAILED"
    assert state.next_attempt_at is None

    with pytest.raises(LeaseUnavailable, match="dead-letter"):
        claim(
            state,
            claimant="dispatcher-b",
            claim_token="lease-11",
            now=now + timedelta(seconds=1),
        )


@pytest.mark.parametrize("seconds", [0, 31])
def test_retry_jitter_must_stay_within_one_to_30_seconds(seconds: int) -> None:
    claimed = claim(
        OutboxState(),
        claimant="dispatcher-a",
        claim_token="lease-a",
        now=NOW,
    )

    with pytest.raises(ValueError, match="retry"):
        mark_publish_failed(
            claimed,
            claim_token="lease-a",
            lease_version=claimed.lease_version,
            now=NOW,
            retry_delay=timedelta(seconds=seconds),
        )
