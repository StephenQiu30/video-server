from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.application.analysis import (
    PersistenceConflict,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)
from app.infrastructure.database.models import OutboxEventRow
from app.infrastructure.database.models.analysis import AnalysisArtifactLockRow
from sqlalchemy import func, select
from tests.unit.infrastructure.analysis.conftest import AnalysisDatabase
from tests.unit.infrastructure.analysis.factories import (
    OWNER,
    analysis_command,
    seed_artifact,
)

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)


async def count_rows(analysis_db: AnalysisDatabase, model: type[object]) -> int:
    async with analysis_db.sessions() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
async def test_job_outbox_and_retention_lock_are_created_atomically(
    analysis_db,
) -> None:
    source = await seed_artifact(analysis_db.sessions, NOW)
    command = analysis_command(source)

    artifact = await analysis_db.repository.get_artifact_for_download(
        source.download_id
    )
    assert artifact is not None
    assert artifact.id == source.artifact_id
    assert artifact.owner_hash == OWNER
    assert await analysis_db.repository.get_artifact_for_download(uuid4()) is None

    created = await analysis_db.repository.create_job_and_enqueue(command, now=NOW)

    assert created.created is True
    assert created.job.artifact_id == source.artifact_id
    assert await count_rows(analysis_db, OutboxEventRow) == 1
    assert await count_rows(analysis_db, AnalysisArtifactLockRow) == 1
    async with analysis_db.sessions() as session:
        event = await session.get(OutboxEventRow, command.outbox_event_id)
        assert event is not None
        assert event.event_type == "analysis.requested"
        assert "transcript" not in event.payload
        assert "owner_hash" not in event.payload
        assert "custom_prompt" not in event.payload


@pytest.mark.asyncio
async def test_custom_prompt_is_persisted_without_entering_outbox(
    analysis_db,
) -> None:
    source = await seed_artifact(analysis_db.sessions, NOW)
    command = replace(
        analysis_command(source),
        custom_prompt="重点识别产品功能演示。",
    )

    created = await analysis_db.repository.create_job_and_enqueue(command, now=NOW)

    assert created.job.custom_prompt == "重点识别产品功能演示。"
    async with analysis_db.sessions() as session:
        event = await session.get(OutboxEventRow, command.outbox_event_id)
        assert event is not None
        assert "custom_prompt" not in event.payload


@pytest.mark.asyncio
async def test_owner_key_is_idempotent_and_rejects_different_input(
    analysis_db,
) -> None:
    source = await seed_artifact(analysis_db.sessions, NOW)
    first = analysis_command(source)
    await analysis_db.repository.create_job_and_enqueue(first, now=NOW)

    key_replay = await analysis_db.repository.create_job_and_enqueue(
        replace(first, id=uuid4(), outbox_event_id=uuid4()),
        now=NOW,
    )
    assert key_replay.created is False
    assert key_replay.job.id == first.id
    assert await count_rows(analysis_db, OutboxEventRow) == 1

    fresh = await analysis_db.repository.create_job_and_enqueue(
        replace(
            first,
            id=uuid4(),
            idempotency_key="new-user-action",
            outbox_event_id=uuid4(),
        ),
        now=NOW,
    )
    assert fresh.created is True
    assert fresh.job.id != first.id
    assert await count_rows(analysis_db, OutboxEventRow) == 2

    with pytest.raises(PersistenceIdempotencyConflict):
        await analysis_db.repository.create_job_and_enqueue(
            replace(
                first,
                id=uuid4(),
                request_fingerprint="c" * 64,
                outbox_event_id=uuid4(),
            ),
            now=NOW,
        )


@pytest.mark.asyncio
async def test_creation_revalidates_status_owner_expiry_and_sha(analysis_db) -> None:
    failed = await seed_artifact(analysis_db.sessions, NOW, status="failed")
    expired = await seed_artifact(
        analysis_db.sessions, NOW, expires_at=NOW - timedelta(seconds=1)
    )
    foreign = await seed_artifact(analysis_db.sessions, NOW, owner_hash="b" * 64)

    for command in (
        analysis_command(failed),
        analysis_command(expired),
        replace(analysis_command(foreign), owner_hash=OWNER),
    ):
        with pytest.raises(PersistenceNotFound):
            await analysis_db.repository.create_job_and_enqueue(command, now=NOW)

    valid = await seed_artifact(analysis_db.sessions, NOW)
    with pytest.raises(PersistenceConflict):
        await analysis_db.repository.create_job_and_enqueue(
            replace(analysis_command(valid), input_sha256="0" * 64), now=NOW
        )
