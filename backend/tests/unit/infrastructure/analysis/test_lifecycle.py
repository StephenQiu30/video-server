from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.application.analysis import PersistenceConflict, PersistenceNotFound
from app.infrastructure.database.models.analysis import AnalysisArtifactLockRow
from sqlalchemy import func, select
from tests.unit.infrastructure.analysis.factories import (
    analysis_command,
    seed_artifact,
)

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)


async def create_job(analysis_db, *, max_attempts: int = 3):
    source = await seed_artifact(analysis_db.sessions, NOW)
    command = analysis_command(source, max_attempts=max_attempts)
    await analysis_db.repository.create_job_and_enqueue(command, now=NOW)
    return source, command


async def lock_count(analysis_db) -> int:
    async with analysis_db.sessions() as session:
        statement = select(func.count()).select_from(AnalysisArtifactLockRow)
        return int(await session.scalar(statement) or 0)


@pytest.mark.asyncio
async def test_claim_and_heartbeat_enforce_lease_stage_and_progress(
    analysis_db,
) -> None:
    _, command = await create_job(analysis_db)
    claimed = await analysis_db.repository.claim_job(
        command.id, "worker-a", NOW, timedelta(seconds=30)
    )
    assert claimed is not None
    assert (claimed.status, claimed.stage, claimed.attempt, claimed.version) == (
        "running",
        "preparing",
        1,
        1,
    )
    assert await analysis_db.repository.heartbeat(
        command.id,
        "worker-a",
        1,
        stage="preparing",
        progress=30,
        now=NOW + timedelta(seconds=1),
        lease_for=timedelta(seconds=30),
    )
    with pytest.raises(PersistenceConflict):
        await analysis_db.repository.heartbeat(
            command.id,
            "worker-a",
            1,
            stage="validating",
            progress=80,
            now=NOW + timedelta(seconds=2),
            lease_for=timedelta(seconds=30),
        )
    with pytest.raises(PersistenceConflict):
        await analysis_db.repository.heartbeat(
            command.id,
            "worker-a",
            1,
            stage="preparing",
            progress=20,
            now=NOW + timedelta(seconds=2),
            lease_for=timedelta(seconds=30),
        )
    with pytest.raises(PersistenceNotFound):
        await analysis_db.repository.cancel_job(command.id, "b" * 64, NOW)

    cancelled = await analysis_db.repository.cancel_job(
        command.id, command.owner_hash, NOW + timedelta(seconds=1)
    )
    assert (cancelled.status, cancelled.error_code) == ("cancelled", "cancelled")
    assert await lock_count(analysis_db) == 0
    assert not await analysis_db.repository.heartbeat(
        command.id,
        "worker-a",
        1,
        stage="preparing",
        progress=20,
        now=NOW + timedelta(seconds=2),
        lease_for=timedelta(seconds=30),
    )


@pytest.mark.asyncio
async def test_retry_keeps_lock_until_terminal_failure(analysis_db) -> None:
    _, command = await create_job(analysis_db, max_attempts=2)
    await analysis_db.repository.claim_job(
        command.id, "worker-a", NOW, timedelta(seconds=30)
    )
    retry_at = NOW + timedelta(seconds=10)
    retrying = await analysis_db.repository.complete_failure(
        command.id,
        "worker-a",
        1,
        error_code="provider_unavailable",
        error_message="temporary",
        retryable=True,
        now=NOW + timedelta(seconds=1),
        retry_at=retry_at,
    )
    assert retrying.status == "retry_wait"
    assert await lock_count(analysis_db) == 1
    assert await analysis_db.repository.release_ready_retries(retry_at, limit=10) == (
        command.id,
    )
    await analysis_db.repository.claim_job(
        command.id, "worker-b", retry_at, timedelta(seconds=30)
    )
    failed = await analysis_db.repository.complete_failure(
        command.id,
        "worker-b",
        2,
        error_code="invalid_model_output",
        error_message="strict schema rejected",
        retryable=False,
        now=retry_at + timedelta(seconds=1),
    )
    assert failed.status == "failed"
    assert await lock_count(analysis_db) == 0

    _, stale = await create_job(analysis_db, max_attempts=1)
    await analysis_db.repository.claim_job(
        stale.id, "dead-worker", NOW, timedelta(seconds=5)
    )
    reclaimed = await analysis_db.repository.reclaim_stale(
        NOW + timedelta(seconds=6), limit=10
    )
    assert reclaimed == (stale.id,)
    stale_job = await analysis_db.repository.get_job(stale.id)
    assert stale_job is not None and stale_job.status == "failed"
    assert await lock_count(analysis_db) == 0
