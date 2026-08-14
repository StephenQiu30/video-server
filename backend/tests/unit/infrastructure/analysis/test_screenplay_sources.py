from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.application.analysis import (
    AnalysisRetry,
    PersistenceArtifactUnavailable,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.infrastructure.database.models import (
    AnalysisArtifactLockRow,
    AnalysisDocumentLockRow,
    AnalysisRunRow,
    DocumentArtifactRow,
    DocumentRow,
    OutboxEventRow,
)
from sqlalchemy import func, select, update
from tests.unit.infrastructure.analysis.factories import OWNER
from tests.unit.infrastructure.analysis.screenplay_factories import (
    screenplay_command,
    seed_screenplay,
)

NOW = datetime(2026, 8, 14, 12, tzinfo=UTC)


async def count_rows(analysis_db, model: type[object]) -> int:
    async with analysis_db.sessions() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
async def test_screenplay_projection_creation_and_lock_are_owner_scoped(
    analysis_db,
) -> None:
    source = await seed_screenplay(analysis_db.sessions, NOW)
    projected = await analysis_db.repository.get_document_for_analysis(
        source.document_id
    )
    assert projected is not None
    assert (
        projected.owner_hash,
        projected.status,
        projected.text_sha256,
        projected.normalized_status,
        projected.normalized_sha256,
    ) == (OWNER, "ready", source.sha256, "ready", source.sha256)
    assert await analysis_db.repository.get_document_for_analysis(uuid4()) is None

    command = screenplay_command(source)
    saved = await analysis_db.repository.create_job_and_enqueue(command, now=NOW)

    assert saved.created is True
    assert saved.job.artifact_id is None
    assert saved.job.document_id == source.document_id
    assert (saved.job.input_kind, saved.job.result_contract) == (
        "screenplay",
        "screenplay-analysis",
    )
    assert await count_rows(analysis_db, AnalysisArtifactLockRow) == 0
    assert await count_rows(analysis_db, AnalysisDocumentLockRow) == 1
    assert await count_rows(analysis_db, OutboxEventRow) == 1


@pytest.mark.asyncio
async def test_screenplay_creation_revalidates_state_owner_expiry_and_sha(
    analysis_db,
) -> None:
    failed = await seed_screenplay(analysis_db.sessions, NOW, status="failed")
    expired = await seed_screenplay(
        analysis_db.sessions, NOW, expires_at=NOW - timedelta(seconds=1)
    )
    foreign = await seed_screenplay(analysis_db.sessions, NOW, owner_hash="b" * 64)
    missing_text = await seed_screenplay(
        analysis_db.sessions, NOW, normalized_status=None
    )
    deleting_text = await seed_screenplay(
        analysis_db.sessions, NOW, normalized_status="deleting"
    )

    for command in (
        screenplay_command(failed),
        screenplay_command(expired),
        replace(screenplay_command(foreign), owner_hash=OWNER),
        screenplay_command(missing_text),
        screenplay_command(deleting_text),
    ):
        with pytest.raises(PersistenceNotFound):
            await analysis_db.repository.create_job_and_enqueue(command, now=NOW)

    valid = await seed_screenplay(analysis_db.sessions, NOW)
    with pytest.raises(PersistenceConflict):
        await analysis_db.repository.create_job_and_enqueue(
            replace(screenplay_command(valid), input_sha256="0" * 64), now=NOW
        )


@pytest.mark.asyncio
async def test_screenplay_retry_recreates_and_terminal_paths_release_lock(
    analysis_db,
) -> None:
    source = await seed_screenplay(analysis_db.sessions, NOW)
    command = screenplay_command(source)
    await analysis_db.repository.create_job_and_enqueue(command, now=NOW)
    await analysis_db.repository.claim_job(
        command.id,
        command.run_id,
        1,
        0,
        "worker-a",
        NOW,
        timedelta(seconds=30),
    )
    failed = await analysis_db.repository.complete_failure(
        command.id,
        "worker-a",
        1,
        error_code="analysis_cli_failed",
        error_message="controlled",
        retryable=False,
        now=NOW + timedelta(seconds=1),
    )
    assert failed.status == "failed"
    assert await count_rows(analysis_db, AnalysisDocumentLockRow) == 0

    retry = AnalysisRetry(
        job_id=command.id,
        run_id=uuid4(),
        owner_hash=command.owner_hash,
        idempotency_key="screenplay-retry",
        trigger="manual_retry",
        outbox_event_id=uuid4(),
        max_attempts=3,
    )
    retried = await analysis_db.repository.retry_job_and_enqueue(
        retry, now=NOW + timedelta(seconds=2)
    )
    assert retried.created is True
    assert await count_rows(analysis_db, AnalysisDocumentLockRow) == 1
    cancelled = await analysis_db.repository.cancel_job(
        command.id, command.owner_hash, NOW + timedelta(seconds=3)
    )
    assert cancelled.status == "cancelled"
    assert await count_rows(analysis_db, AnalysisDocumentLockRow) == 0


@pytest.mark.asyncio
async def test_screenplay_retry_fails_closed_after_input_expiry(analysis_db) -> None:
    source = await seed_screenplay(analysis_db.sessions, NOW)
    command = screenplay_command(source)
    await analysis_db.repository.create_job_and_enqueue(command, now=NOW)
    await analysis_db.repository.cancel_job(command.id, command.owner_hash, NOW)
    async with analysis_db.sessions() as session, session.begin():
        await session.execute(
            update(DocumentRow)
            .where(DocumentRow.id == source.document_id)
            .values(expires_at=NOW - timedelta(seconds=1))
        )
        await session.execute(
            update(DocumentArtifactRow)
            .where(DocumentArtifactRow.document_id == source.document_id)
            .values(expires_at=NOW - timedelta(seconds=1))
        )

    with pytest.raises(PersistenceArtifactUnavailable):
        await analysis_db.repository.retry_job_and_enqueue(
            AnalysisRetry(
                job_id=command.id,
                run_id=uuid4(),
                owner_hash=command.owner_hash,
                idempotency_key="expired-retry",
                trigger="manual_retry",
                outbox_event_id=uuid4(),
                max_attempts=3,
            ),
            now=NOW + timedelta(seconds=1),
        )
    assert await count_rows(analysis_db, AnalysisRunRow) == 1
    assert await count_rows(analysis_db, AnalysisDocumentLockRow) == 0
