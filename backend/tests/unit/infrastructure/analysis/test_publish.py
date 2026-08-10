from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from app.application.analysis import AnalysisPublish, PersistenceConflict
from app.infrastructure.database.models.analysis import (
    AnalysisArtifactLockRow,
    AnalysisResultRow,
)
from sqlalchemy import func, select
from tests.unit.infrastructure.analysis.factories import (
    analysis_command,
    analysis_result,
    seed_artifact,
)

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)


async def validating_job(analysis_db):
    source = await seed_artifact(analysis_db.sessions, NOW)
    command = analysis_command(source)
    await analysis_db.repository.create_job_and_enqueue(command, now=NOW)
    current = await analysis_db.repository.claim_job(
        command.id, "worker-a", NOW, timedelta(seconds=30)
    )
    assert current is not None
    for offset, stage, progress in (
        (1, "analyzing", 70),
        (2, "validating", 90),
    ):
        assert await analysis_db.repository.heartbeat(
            command.id,
            "worker-a",
            1,
            stage=stage,
            progress=progress,
            now=NOW + timedelta(seconds=offset),
            lease_for=timedelta(seconds=30),
        )
    job = await analysis_db.repository.get_job(command.id)
    assert job is not None
    return command, job


async def row_count(analysis_db, model: type[object]) -> int:
    async with analysis_db.sessions() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
async def test_result_and_success_publish_atomically_without_transcript(
    analysis_db,
) -> None:
    command, job = await validating_job(analysis_db)
    publish = AnalysisPublish(
        job_id=command.id,
        result=analysis_result(),
        lease_owner="worker-a",
        expected_version=job.version,
        provider="codex",
        model="controlled-model",
        cli_version="codex-cli controlled",
        now=NOW + timedelta(seconds=3),
    )

    succeeded = await analysis_db.repository.publish_result(publish)

    assert (succeeded.status, succeeded.progress) == ("succeeded", 100)
    assert await row_count(analysis_db, AnalysisArtifactLockRow) == 0
    assert await row_count(analysis_db, AnalysisResultRow) == 1
    async with analysis_db.sessions() as session:
        row = await session.scalar(
            select(AnalysisResultRow).where(AnalysisResultRow.job_id == command.id)
        )
        assert row is not None
        assert (row.provider, row.model) == (
            "codex",
            "controlled-model",
        )
        assert set(row.result_json) == {
            "language",
            "title",
            "summary",
            "media",
            "shot_count",
            "shots",
            "highlights",
            "assets",
            "production_advice",
        }
        serialized = json.dumps(row.result_json, ensure_ascii=False).lower()
        assert "transcript" not in serialized
        assert "provider_response" not in serialized
    assert await analysis_db.repository.get_result(command.id) == publish.result

    replay = await analysis_db.repository.publish_result(publish)
    assert replay.status == "succeeded"
    assert await row_count(analysis_db, AnalysisResultRow) == 1

    changed = replace(analysis_result(), title="不同输出")
    with pytest.raises(PersistenceConflict):
        await analysis_db.repository.publish_result(replace(publish, result=changed))


@pytest.mark.asyncio
async def test_publish_requires_matching_validating_lease_and_version(
    analysis_db,
) -> None:
    command, job = await validating_job(analysis_db)
    valid = AnalysisPublish(
        job_id=command.id,
        result=analysis_result(),
        lease_owner="worker-a",
        expected_version=job.version,
        provider="codex",
        model="controlled-model",
        cli_version="codex-cli controlled",
        now=NOW + timedelta(seconds=3),
    )

    for invalid in (
        replace(valid, lease_owner="worker-b"),
        replace(valid, expected_version=job.version - 1),
        replace(valid, now=NOW + timedelta(minutes=1)),
    ):
        with pytest.raises(PersistenceConflict):
            await analysis_db.repository.publish_result(invalid)
        assert await row_count(analysis_db, AnalysisResultRow) == 0
