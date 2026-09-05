from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.application.analysis import AnalysisRetry, PersistenceRetryLimited
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database.models import AnalysisRunRow
from sqlalchemy import func, select
from tests.unit.infrastructure.analysis.factories import analysis_command, seed_artifact

NOW = datetime(2026, 9, 5, tzinfo=UTC)


async def test_concurrent_different_jobs_share_one_owner_retry_budget(analysis_db):
    commands = []
    for index in range(2):
        source = await seed_artifact(analysis_db.sessions, NOW)
        initial = analysis_command(source)
        repo = analysis_db.repository
        await repo.create_job_and_enqueue(initial, now=NOW)
        await repo.claim_job(
            initial.id, initial.run_id, 1, 0, "worker", NOW, timedelta(seconds=30)
        )
        await repo.complete_failure(
            initial.id,
            "worker",
            1,
            error_code="analysis_cli_failed",
            error_message="failed",
            retryable=False,
            now=NOW + timedelta(seconds=1),
        )
        commands.append(
            AnalysisRetry(
                job_id=initial.id,
                run_id=uuid4(),
                owner_hash=initial.owner_hash,
                idempotency_key=f"retry-{index}",
                trigger="manual_retry",
                outbox_event_id=uuid4(),
                max_attempts=3,
                retries_per_day=1,
            )
        )

    class ConcurrentRepository(SqlAlchemyAnalysisRepository):
        @staticmethod
        async def _require_retry_capacity(session, row, command, now):
            await SqlAlchemyAnalysisRepository._require_retry_capacity(
                session, row, command, now
            )
            # Yield after reading the count: without the owner lock both
            # transactions see zero before either creates its next run.
            await asyncio.sleep(0.1)

    repo = ConcurrentRepository(analysis_db.sessions)
    results = await asyncio.wait_for(
        asyncio.gather(
            *(
                repo.retry_job_and_enqueue(command, now=NOW + timedelta(seconds=2))
                for command in commands
            ),
            return_exceptions=True,
        ),
        timeout=10,
    )
    assert sum(isinstance(result, PersistenceRetryLimited) for result in results) == 1
    assert (
        sum(
            not isinstance(result, BaseException) and result.created
            for result in results
        )
        == 1
    )
    async with analysis_db.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AnalysisRunRow)
                .where(AnalysisRunRow.trigger == "manual_retry")
            )
            == 1
        )

    successful = next(
        command
        for command, result in zip(commands, results, strict=True)
        if not isinstance(result, BaseException)
    )
    replay = await repo.retry_job_and_enqueue(
        successful, now=NOW + timedelta(seconds=3)
    )
    assert replay.created is False
