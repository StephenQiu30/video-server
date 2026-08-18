from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.infrastructure.database.models import (
    AnalysisArtifactLockRow,
    AnalysisJobRow,
    ArtifactRow,
)
from app.infrastructure.storage_file_repository import SqlAlchemyStorageFileRepository
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from tests.unit.infrastructure.analytics_helpers import add_job

NOW = datetime(2026, 8, 18, 12, tzinfo=UTC)
OWNER = "a" * 64


@pytest.mark.asyncio
async def test_storage_files_page_and_manual_cleanup_respect_analysis_lock(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    await add_job(
        sessions,
        extractor="Youtube",
        owner=OWNER,
        status="succeeded",
        created_at=NOW - timedelta(days=31),
        duration=30,
        size_bytes=1_024,
    )
    await add_job(
        sessions,
        extractor="Vimeo",
        owner=OWNER,
        status="succeeded",
        created_at=NOW - timedelta(days=5),
        duration=45,
        size_bytes=2_048,
    )
    async with sessions() as session, session.begin():
        old_artifact = await session.scalar(
            select(ArtifactRow).order_by(ArtifactRow.created_at)
        )
        assert old_artifact is not None
        analysis_id, run_id = uuid4(), uuid4()
        session.add(
            AnalysisJobRow(
                id=analysis_id,
                artifact_id=old_artifact.id,
                owner_hash=OWNER,
                idempotency_key="locked-analysis",
                request_fingerprint="e" * 64,
                input_sha256=old_artifact.sha256,
                skill_id="director-breakdown",
                skill_instructions="controlled",
                skill_instructions_sha256="f" * 64,
                output_language="zh-CN",
                status="running",
                progress=10,
                active_run_id=run_id,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            AnalysisArtifactLockRow(
                job_id=analysis_id,
                artifact_id=old_artifact.id,
                created_at=NOW,
            )
        )

    repository = SqlAlchemyStorageFileRepository(sessions)
    first_page = await repository.list_files(page=1, page_size=1)
    second_page = await repository.list_files(page=2, page_size=1)
    assert first_page.total == second_page.total == 2
    assert first_page.items[0].size_bytes == 2_048
    assert second_page.items[0].size_bytes == 1_024

    deleted: list[str] = []

    async def delete_object(key: str) -> None:
        deleted.append(key)

    locked = await repository.cleanup_before(
        NOW - timedelta(days=30), now=NOW, delete=delete_object
    )
    assert locked.removed_resources == 0
    assert deleted == []

    async with sessions() as session, session.begin():
        await session.execute(delete(AnalysisArtifactLockRow))
    cleaned = await repository.cleanup_before(
        NOW - timedelta(days=30), now=NOW, delete=delete_object
    )
    assert cleaned.removed_resources == cleaned.removed_objects == 1
    assert cleaned.freed_bytes == 1_024
    assert cleaned.failed_resources == 0
    assert len(deleted) == 1
    remaining = await repository.list_files(page=1, page_size=20)
    assert remaining.total == 1
    assert remaining.items[0].size_bytes == 2_048
