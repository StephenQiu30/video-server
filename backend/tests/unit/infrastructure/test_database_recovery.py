from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.infrastructure.database import (
    DownloadCreate,
    FormatCreate,
    InspectionCreate,
    SqlAlchemyDownloadRepository,
)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@pytest.fixture
async def repository(postgres_engine: AsyncEngine) -> SqlAlchemyDownloadRepository:
    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    yield SqlAlchemyDownloadRepository(factory)


async def _queued_job(repository, *, max_attempts: int = 3):
    now = datetime.now(UTC)
    inspection_id, format_id, job_id = uuid4(), uuid4(), uuid4()
    await repository.save_inspection(
        InspectionCreate(
            id=inspection_id,
            owner_hash="a" * 64,
            idempotency_key=str(uuid4()),
            request_fingerprint="e" * 64,
            url_ciphertext=b"cipher",
            url_nonce=b"nonce",
            url_key_id="primary",
            extractor_key="Youtube",
            provider_media_id="controlled",
            title="Video",
            duration_seconds=30,
            metadata={},
            expires_at=now + timedelta(minutes=15),
            formats=(
                FormatCreate(
                    id=format_id,
                    display_name="720p",
                    plan_fingerprint="b" * 64,
                    semantic_plan={"height": 720},
                    provider_hints={},
                    expires_at=now + timedelta(minutes=15),
                ),
            ),
        )
    )
    await repository.create_job(
        DownloadCreate(
            id=job_id,
            inspection_id=inspection_id,
            format_id=format_id,
            owner_hash="a" * 64,
            idempotency_key=str(uuid4()),
            request_fingerprint="c" * 64,
            semantic_plan={"height": 720},
            max_attempts=max_attempts,
        ),
        now=now,
    )
    return job_id, now


@pytest.mark.asyncio
async def test_stale_queued_job_is_republished_without_changing_identity(
    repository,
) -> None:
    job_id, now = await _queued_job(repository)
    initial = await repository.claim_outbox(
        "publisher", now, timedelta(seconds=30), limit=10
    )
    assert await repository.mark_outbox_published(initial[0].id, "publisher", now)

    assert await repository.recover_stale_queued(
        now + timedelta(seconds=59), now, limit=10
    ) == (job_id,)
    recovered = await repository.claim_outbox(
        "publisher",
        now + timedelta(seconds=59),
        timedelta(seconds=30),
        limit=10,
    )
    assert len(recovered) == 1
    assert recovered[0].aggregate_id == job_id
    assert recovered[0].payload["version"] == 0
    assert (await repository.get_job(job_id)).version == 0


@pytest.mark.asyncio
async def test_stale_lease_is_requeued_with_a_new_outbox_event(repository) -> None:
    job_id, now = await _queued_job(repository)
    initial = await repository.claim_outbox(
        "publisher", now, timedelta(seconds=30), limit=10
    )
    assert len(initial) == 1
    assert await repository.mark_outbox_published(initial[0].id, "publisher", now)
    await repository.claim_job(job_id, "dead-worker", now, timedelta(seconds=30))

    reclaimed = await repository.reclaim_stale(now + timedelta(seconds=31), limit=10)
    assert reclaimed == (job_id,)
    assert (await repository.get_job(job_id)).status == "retry_wait"
    assert await repository.release_ready_retries(
        now + timedelta(seconds=31), limit=10
    ) == (job_id,)
    assert (await repository.get_job(job_id)).status == "queued"

    events = await repository.claim_outbox(
        "publisher", now + timedelta(seconds=31), timedelta(seconds=30), limit=10
    )
    assert len(events) == 1
    assert all(event.event_type == "download.requested" for event in events)

    first = events[0]
    assert first.publish_attempts == 1
    assert await repository.mark_outbox_failed(
        first.id,
        "publisher",
        now + timedelta(seconds=32),
        "broker unavailable",
        now + timedelta(seconds=40),
    )
    retried = await repository.claim_outbox(
        "publisher", now + timedelta(seconds=41), timedelta(seconds=30), limit=10
    )
    failed_event = next(item for item in retried if item.id == first.id)
    assert failed_event.publish_attempts == 2
    assert await repository.mark_outbox_published(
        failed_event.id, "publisher", now + timedelta(seconds=42)
    )


@pytest.mark.asyncio
async def test_stale_last_attempt_fails_without_requeue(repository) -> None:
    job_id, now = await _queued_job(repository, max_attempts=1)
    await repository.claim_job(job_id, "dead-worker", now, timedelta(seconds=30))

    assert await repository.reclaim_stale(now + timedelta(seconds=31), limit=10) == (
        job_id,
    )
    job = await repository.get_job(job_id)
    assert (job.status, job.error_code) == ("failed", "worker_lost")


@pytest.mark.asyncio
async def test_retryable_failure_waits_before_outbox_release(repository) -> None:
    job_id, now = await _queued_job(repository)
    await repository.claim_job(job_id, "worker", now, timedelta(seconds=30))
    retry_at = now + timedelta(seconds=20)

    failed = await repository.complete_failure(
        job_id,
        "worker",
        1,
        error_code="storage_unavailable",
        error_message="temporary storage failure",
        retryable=True,
        now=now + timedelta(seconds=1),
        retry_at=retry_at,
    )
    assert (failed.status, failed.retry_at) == ("retry_wait", retry_at)
    assert (
        await repository.release_ready_retries(
            retry_at - timedelta(seconds=1), limit=10
        )
        == ()
    )
    assert await repository.release_ready_retries(retry_at, limit=10) == (job_id,)
    assert (await repository.get_job(job_id)).status == "queued"
