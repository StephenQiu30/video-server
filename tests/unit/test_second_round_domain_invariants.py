from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from video_server.job.idempotency import (
    ResolutionRequest,
    digest_idempotency_key,
    digest_resolution_request,
)
from video_server.job.lease import LEASE_RENEWAL_INTERVAL, renew_lease
from video_server.job.outbox import (
    LEASE_DURATION,
    MAX_PUBLISH_ATTEMPTS,
    OutboxState,
    StaleClaim,
    claim,
    mark_publish_failed,
    mark_published,
)
from video_server.job.state import JobStage, JobState, JobStatus
from video_server.source.retention import RetentionClass, retention_deadlines

NOW = datetime(2026, 7, 18, tzinfo=UTC)
HMAC_KEY = b"\x11" * 32
REQUEST = ResolutionRequest(
    url="https://media.example/video",
    rights_confirmed=True,
    rights_statement_version="rights-2026-07-18.1",
    rights_statement_locale="zh-CN",
)


def _claimed(*, attempts: int = 0, token: str = "lease-a") -> OutboxState:
    return claim(
        OutboxState(attempts=attempts),
        claimant="dispatcher-a",
        claim_token=token,
        now=NOW,
    )


def test_expired_lease_cannot_reuse_its_fencing_token() -> None:
    claimed = _claimed()

    with pytest.raises(StaleClaim, match="token"):
        claim(
            claimed,
            claimant="dispatcher-b",
            claim_token="lease-a",
            now=NOW + LEASE_DURATION,
        )


def test_tenth_claim_crash_dead_letters_when_lease_expires() -> None:
    claimed = _claimed(attempts=MAX_PUBLISH_ATTEMPTS - 1, token="lease-10")

    settled = claim(
        claimed,
        claimant="dispatcher-b",
        claim_token="lease-11",
        now=NOW + LEASE_DURATION,
    )

    assert settled.dead_lettered_at == NOW + LEASE_DURATION
    assert settled.terminal_error_code == "QUEUE_DELIVERY_FAILED"
    assert settled.claim_token is None


def test_renewal_at_20_seconds_extends_lease_without_an_attempt() -> None:
    claimed = _claimed()
    renewal_time = NOW + LEASE_RENEWAL_INTERVAL

    renewed = renew_lease(claimed, claim_token="lease-a", now=renewal_time)

    assert timedelta(seconds=20) == LEASE_RENEWAL_INTERVAL
    assert renewed.lease_expires_at == renewal_time + LEASE_DURATION
    assert renewed.claimed_at == claimed.claimed_at
    assert renewed.attempts == claimed.attempts


def test_renewal_rejects_stale_and_expired_tokens() -> None:
    claimed = _claimed()

    with pytest.raises(StaleClaim, match="token"):
        renew_lease(claimed, claim_token="lease-old", now=NOW + timedelta(seconds=20))
    with pytest.raises(StaleClaim, match="expired"):
        renew_lease(claimed, claim_token="lease-a", now=NOW + LEASE_DURATION)


def test_renewal_rejects_time_before_claim() -> None:
    with pytest.raises(ValueError, match="claim"):
        renew_lease(
            _claimed(),
            claim_token="lease-a",
            now=NOW - timedelta(microseconds=1),
        )


def test_completion_and_failure_cannot_precede_claim() -> None:
    claimed = _claimed()
    before_claim = NOW - timedelta(microseconds=1)

    with pytest.raises(ValueError, match="claim"):
        mark_published(claimed, claim_token="lease-a", now=before_claim)
    with pytest.raises(ValueError, match="claim"):
        mark_publish_failed(
            claimed,
            claim_token="lease-a",
            now=before_claim,
            retry_delay=timedelta(seconds=1),
        )


def test_active_lease_requires_a_consumed_attempt() -> None:
    with pytest.raises(ValueError, match="attempt"):
        OutboxState(
            claimed_by="dispatcher-a",
            claim_token="lease-a",
            claimed_at=NOW,
            lease_expires_at=NOW + LEASE_DURATION,
        )


def test_retry_and_published_states_require_a_consumed_attempt() -> None:
    with pytest.raises(ValueError, match="attempt"):
        OutboxState(next_attempt_at=NOW)
    with pytest.raises(ValueError, match="attempt"):
        OutboxState(published_at=NOW)


@pytest.mark.parametrize("month,day", [(3, 7), (10, 31)])
@pytest.mark.parametrize(
    ("retention_class", "eligible_after", "purge_after"),
    [
        (RetentionClass.RESOLUTION_DETAIL, timedelta(days=6, hours=22), timedelta(days=7)),
        (RetentionClass.RESOLUTION_AUDIT, timedelta(days=29, hours=22), timedelta(days=30)),
    ],
)
def test_retention_deadlines_are_absolute_across_dst(
    month: int,
    day: int,
    retention_class: RetentionClass,
    eligible_after: timedelta,
    purge_after: timedelta,
) -> None:
    created_at = datetime(2026, month, day, 12, tzinfo=ZoneInfo("America/New_York"))
    created_utc = created_at.astimezone(UTC)

    deadlines = retention_deadlines(retention_class, created_at=created_at)

    assert deadlines.eligible_at.astimezone(UTC) == created_utc + eligible_after
    assert deadlines.must_purge_by.astimezone(UTC) == created_utc + purge_after


def test_request_digest_canonicalizes_equivalent_https_urls() -> None:
    variant = replace(REQUEST, url="https://MEDIA.EXAMPLE:443/%7euser?q=%7e")
    canonical = replace(REQUEST, url="https://media.example/~user?q=~")

    assert digest_resolution_request(variant, hmac_key=HMAC_KEY) == (
        digest_resolution_request(canonical, hmac_key=HMAC_KEY)
    )


@pytest.mark.parametrize(
    ("stage", "progress"),
    [
        (JobStage.CHECKING_POLICY, None),
        (JobStage.VALIDATING_URL, 0),
        (JobStage.NORMALIZING_FORMATS, 100),
    ],
)
def test_unstarted_failure_preserves_the_initial_job_snapshot(
    stage: JobStage,
    progress: int | None,
) -> None:
    with pytest.raises(ValueError, match="failed"):
        JobState(JobStatus.FAILED, stage, attempt=0, progress=progress)


@pytest.mark.parametrize(
    "raw_key",
    [" " * 16, "resolve 20260718 0001", "resolve-20260718-0001 "],
)
def test_idempotency_key_rejects_space(raw_key: str) -> None:
    with pytest.raises(ValueError, match="ASCII"):
        digest_idempotency_key(raw_key, hmac_key=HMAC_KEY)
