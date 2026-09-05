from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.application.quotas import QuotaExceeded, QuotaPolicy
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database import (
    DownloadCreate,
    SqlAlchemyDocumentImportRepository,
    SqlAlchemyDownloadRepository,
    SqlAlchemyMediaImportRepository,
)
from app.infrastructure.database.models import (
    ArtifactRow,
    DocumentRow,
    DownloadJobRow,
    ResourceAdmissionRow,
)
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.unit.infrastructure.analysis.factories import analysis_command, seed_artifact
from tests.unit.infrastructure.test_document_import_repository import (
    command as document,
)
from tests.unit.infrastructure.test_media_import_repository import command as media

NOW = datetime(2026, 9, 5, tzinfo=UTC)


@pytest.fixture
async def sessions(postgres_engine):
    return async_sessionmaker(postgres_engine, expire_on_commit=False)


async def test_cross_kind_concurrent_admission_and_replay(sessions):
    policy = QuotaPolicy(max_active_per_owner=1)
    video = SqlAlchemyMediaImportRepository(sessions, quota_policy=policy)
    doc = SqlAlchemyDocumentImportRepository(sessions, quota_policy=policy)
    results = await asyncio.wait_for(
        asyncio.gather(
            video.create_resource(media(), now=NOW),
            doc.create_resource(document(), now=NOW),
            return_exceptions=True,
        ),
        timeout=10,
    )
    assert sum(isinstance(item, QuotaExceeded) for item in results) == 1
    denied = next(item for item in results if isinstance(item, QuotaExceeded))
    assert denied.code == "active_task_quota_exceeded"
    async with sessions() as session:
        assert await session.scalar(select(func.count(ResourceAdmissionRow.id))) == 1
        count = await session.scalar(select(func.count(DownloadJobRow.id)))
        count += await session.scalar(select(func.count(DocumentRow.id)))
        assert count == 1
    winner, command = (
        (video, media()) if not isinstance(results[0], Exception) else (doc, document())
    )
    replay = await winner.create_resource(command, now=NOW)
    assert not replay.created


async def test_global_capacity_serializes_different_owners(sessions):
    repo = SqlAlchemyMediaImportRepository(
        sessions, quota_policy=QuotaPolicy(max_active_global=1)
    )
    commands = [
        replace(media(), id=uuid4(), owner_hash=owner * 64) for owner in ("a", "b")
    ]
    results = await asyncio.gather(
        *(repo.create_resource(command, now=NOW) for command in commands),
        return_exceptions=True,
    )
    denied = [result for result in results if isinstance(result, QuotaExceeded)]
    assert len(denied) == 1
    assert denied[0].code == "service_capacity_exceeded"


@pytest.mark.parametrize(
    ("policy", "code"),
    [
        (QuotaPolicy(daily_tasks=1), "daily_task_quota_exceeded"),
        (QuotaPolicy(daily_bytes=10_000_000), "daily_byte_quota_exceeded"),
    ],
)
async def test_delete_cannot_refund_rolling_daily_budget(sessions, policy, code):
    repo = SqlAlchemyMediaImportRepository(sessions, quota_policy=policy)
    first = media()
    await repo.create_resource(first, now=NOW)
    async with sessions() as session, session.begin():
        # A physical resource deletion still cannot erase the admission ledger.
        await session.execute(
            delete(DownloadJobRow).where(DownloadJobRow.id == first.id)
        )
    second = replace(first, id=uuid4(), idempotency_key="second")
    with pytest.raises(QuotaExceeded, match=code):
        await repo.create_resource(second, now=NOW + timedelta(hours=1))
    assert (await repo.create_resource(second, now=NOW + timedelta(days=1))).created


async def test_cancel_releases_slot_and_reserved_storage(sessions):
    first = media()
    reserved = first.declared_size_bytes + QuotaPolicy().thumbnail_bytes
    policy = QuotaPolicy(max_active_per_owner=1, storage_bytes=reserved)
    repo = SqlAlchemyMediaImportRepository(sessions, quota_policy=policy)
    await repo.create_resource(first, now=NOW)
    await repo.cancel_resource(first.id, first.owner_hash, first.content_kind, now=NOW)
    assert (
        await repo.create_resource(
            replace(first, id=uuid4(), idempotency_key="second"), now=NOW
        )
    ).created


async def test_first_analysis_and_replay_share_persistent_attempt_budget(sessions):
    policy = QuotaPolicy(daily_analysis_attempts=3)
    repo = SqlAlchemyAnalysisRepository(sessions, quota_policy=policy)
    source = await seed_artifact(sessions, NOW)
    command = analysis_command(source)
    await repo.create_job_and_enqueue(command, now=NOW)
    assert not (await repo.create_job_and_enqueue(command, now=NOW)).created
    second = replace(
        command,
        id=uuid4(),
        run_id=uuid4(),
        idempotency_key="second",
        outbox_event_id=uuid4(),
    )
    with pytest.raises(QuotaExceeded, match="analysis_budget_exceeded"):
        await repo.create_job_and_enqueue(second, now=NOW)
    async with sessions() as session:
        assert await session.scalar(select(func.count(ResourceAdmissionRow.id))) == 1


async def test_download_requires_budget_before_job_and_outbox_creation(sessions):
    source = await seed_artifact(sessions, NOW)
    async with sessions() as session:
        job = await session.get(DownloadJobRow, source.download_id)
    command = DownloadCreate(
        id=uuid4(),
        inspection_id=job.inspection_id,
        format_id=job.format_id,
        owner_hash=job.owner_hash,
        idempotency_key="new",
        request_fingerprint="x" * 64,
        semantic_plan=job.semantic_plan,
    )
    repo = SqlAlchemyDownloadRepository(
        sessions, quota_policy=QuotaPolicy(daily_bytes=1)
    )
    with pytest.raises(QuotaExceeded, match="daily_byte_quota_exceeded"):
        await repo.create_job(command, now=NOW)
    async with sessions() as session:
        assert await session.get(DownloadJobRow, command.id) is None
        assert await session.get(ResourceAdmissionRow, command.id) is None


async def test_download_tombstone_remains_charged_until_physical_cleanup(sessions):
    source = await seed_artifact(sessions, NOW)
    command = media()
    reserved = command.declared_size_bytes + QuotaPolicy().thumbnail_bytes
    repo = SqlAlchemyMediaImportRepository(
        sessions, quota_policy=QuotaPolicy(storage_bytes=reserved)
    )
    async with sessions() as session, session.begin():
        await session.execute(
            update(ArtifactRow)
            .where(ArtifactRow.id == source.artifact_id)
            .values(deleted_at=NOW)
        )
    with pytest.raises(QuotaExceeded, match="storage_quota_exceeded"):
        await repo.create_resource(command, now=NOW)
    async with sessions() as session, session.begin():
        await session.execute(
            delete(ArtifactRow).where(ArtifactRow.id == source.artifact_id)
        )
    assert (await repo.create_resource(command, now=NOW)).created
