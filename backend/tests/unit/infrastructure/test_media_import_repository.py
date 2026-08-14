from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.imports import (
    ImportCleanupRef,
    ImportPersistenceConflict,
    ImportPersistenceIdempotencyConflict,
    ImportResourceCreate,
)
from app.application.imports.events import CONTENT_IMPORT_VERIFY_REQUESTED
from app.domain.imports import (
    ContentKind,
    ImportErrorCode,
    ImportSourceFormat,
    ImportStatus,
    quarantine_object_key,
)
from app.infrastructure.database import (
    Base,
    SqlAlchemyDownloadRepository,
    SqlAlchemyMediaImportRepository,
)
from app.infrastructure.database.models import (
    DownloadJobRow,
    MediaImportAttemptRow,
    MediaImportRow,
    OutboxEventRow,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

NOW = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
RESOURCE_ID = UUID("11111111-1111-4111-8111-111111111111")
SECOND_ID = UUID("22222222-2222-4222-8222-222222222222")
OWNER_HASH = "a" * 64
FIVE_MIB = 5 * 1024**2
DECLARED_SIZE = FIVE_MIB + 1


@pytest.fixture
async def repositories() -> tuple[
    SqlAlchemyMediaImportRepository,
    SqlAlchemyDownloadRepository,
    async_sessionmaker,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    yield (
        SqlAlchemyMediaImportRepository(sessions),
        SqlAlchemyDownloadRepository(sessions),
        sessions,
    )
    await engine.dispose()


def command(
    *,
    resource_id: UUID = RESOURCE_ID,
    fingerprint: str = "b" * 64,
    idempotency_key: str = "upload-1",
) -> ImportResourceCreate:
    return ImportResourceCreate(
        id=resource_id,
        owner_hash=OWNER_HASH,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        content_kind=ContentKind.VIDEO,
        source_format=ImportSourceFormat.MP4,
        display_name="example.mp4",
        content_type="video/mp4",
        declared_size_bytes=DECLARED_SIZE,
        declared_sha256="c" * 64,
        rights_statement_version="content-rights-v1",
    )


async def test_create_is_idempotent_and_creates_browser_download_projection(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, _, sessions = repositories

    created = await repository.create_resource(command(), now=NOW)
    replay = await repository.create_resource(
        command(resource_id=SECOND_ID), now=NOW + timedelta(seconds=1)
    )

    assert created.created is True
    assert replay.created is False
    assert replay.resource.id == RESOURCE_ID
    assert replay.resource.status == ImportStatus.UPLOADING.value
    async with sessions() as session:
        job = await session.get(DownloadJobRow, RESOURCE_ID)
        stored = await session.get(MediaImportRow, RESOURCE_ID)
        outbox_count = await session.scalar(select(func.count(OutboxEventRow.id)))
    assert job is not None
    assert job.source_kind == "browser_import"
    assert job.inspection_id is None
    assert job.format_id is None
    assert job.status == "running"
    assert job.stage == "downloading"
    assert stored is not None
    assert stored.rights_statement_version == "content-rights-v1"
    # SQLite has no PostgreSQL task-event trigger. More importantly, creation
    # does not enqueue the remote downloader's download.requested event.
    assert outbox_count == 0


async def test_create_rejects_idempotency_fingerprint_mismatch(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, _, _ = repositories
    await repository.create_resource(command(), now=NOW)

    with pytest.raises(ImportPersistenceIdempotencyConflict):
        await repository.create_resource(
            command(resource_id=SECOND_ID, fingerprint="d" * 64),
            now=NOW,
        )


async def test_complete_atomically_marks_verifying_and_writes_one_outbox_event(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, _, sessions = repositories
    await repository.create_resource(command(), now=NOW)
    begun = await repository.begin_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        part_size_bytes=FIVE_MIB,
        part_count=2,
        expires_at=NOW + timedelta(minutes=15),
        now=NOW,
    )
    await repository.activate_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        begun.attempt.attempt,
        upload_id="multipart-1",
        now=NOW,
    )

    verifying = await repository.mark_verifying(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        1,
        actual_size_bytes=DECLARED_SIZE,
        now=NOW + timedelta(seconds=1),
    )
    replay = await repository.mark_verifying(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        1,
        actual_size_bytes=DECLARED_SIZE,
        now=NOW + timedelta(seconds=2),
    )

    assert verifying.status == ImportStatus.VERIFYING.value
    assert replay.version == verifying.version
    assert verifying.active_attempt is not None
    assert verifying.active_attempt.status == ImportStatus.VERIFYING.value
    async with sessions() as session:
        events = tuple((await session.scalars(select(OutboxEventRow))).all())
        job = await session.get(DownloadJobRow, RESOURCE_ID)
    assert len(events) == 1
    assert events[0].event_type == CONTENT_IMPORT_VERIFY_REQUESTED
    assert events[0].aggregate_type == "media_import"
    assert events[0].payload == {
        "resource_id": str(RESOURCE_ID),
        "content_kind": "video",
        "attempt": 1,
        "version": verifying.version,
    }
    assert job is not None
    assert (job.status, job.stage, job.stage_rank) == ("running", "verifying", 4)


async def test_refresh_supersedes_only_current_attempt_with_cleanup_reference(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, _, sessions = repositories
    await repository.create_resource(command(), now=NOW)
    first = await repository.begin_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        part_size_bytes=FIVE_MIB,
        part_count=2,
        expires_at=NOW + timedelta(minutes=15),
        now=NOW,
    )
    await repository.activate_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        1,
        upload_id="multipart-1",
        now=NOW,
    )

    second = await repository.begin_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        part_size_bytes=FIVE_MIB,
        part_count=2,
        expires_at=NOW + timedelta(minutes=16),
        now=NOW + timedelta(minutes=1),
    )

    assert second.attempt.attempt == 2
    assert second.attempt.object_key == quarantine_object_key(
        ContentKind.VIDEO, RESOURCE_ID, 2
    )
    assert second.superseded == (
        # The storage cleanup happens only after this database transaction.
        ImportCleanupRef(first.attempt.object_key, "multipart-1"),
    )
    async with sessions() as session:
        stale = await session.get(MediaImportAttemptRow, (RESOURCE_ID, 1))
    assert stale is not None
    assert stale.status == ImportStatus.EXPIRED.value


async def test_retryable_failure_keeps_resource_uploadable_and_cancel_retries_cleanup(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, _, _ = repositories
    await repository.create_resource(command(), now=NOW)
    await repository.begin_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        part_size_bytes=FIVE_MIB,
        part_count=2,
        expires_at=NOW + timedelta(minutes=15),
        now=NOW,
    )
    await repository.activate_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        1,
        upload_id="multipart-1",
        now=NOW,
    )

    failed = await repository.fail_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        1,
        error_code=ImportErrorCode.STORAGE_UNAVAILABLE,
        now=NOW + timedelta(seconds=1),
    )
    assert failed.status == ImportStatus.UPLOADING.value
    assert failed.active_attempt is None

    refreshed = await repository.begin_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        part_size_bytes=FIVE_MIB,
        part_count=2,
        expires_at=NOW + timedelta(minutes=16),
        now=NOW + timedelta(minutes=1),
    )
    await repository.activate_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        refreshed.attempt.attempt,
        upload_id="multipart-2",
        now=NOW + timedelta(minutes=1),
    )
    cancelled = await repository.cancel_resource(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        now=NOW + timedelta(minutes=2),
    )
    replay = await repository.cancel_resource(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.VIDEO,
        now=NOW + timedelta(minutes=3),
    )

    assert cancelled.resource.status == ImportStatus.CANCELLED.value
    assert cancelled.resource.error_code is None
    assert cancelled.cleanup[0].upload_id == "multipart-2"
    assert replay.cleanup == cancelled.cleanup


async def test_remote_download_claim_and_recovery_ignore_browser_import_jobs(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, downloads, sessions = repositories
    await repository.create_resource(command(), now=NOW)
    async with sessions() as session, session.begin():
        job = await session.get(DownloadJobRow, RESOURCE_ID)
        assert job is not None
        job.status = "queued"
        job.stage = None
        job.stage_rank = 0
        job.lease_expires_at = NOW - timedelta(minutes=1)

    claimed = await downloads.claim_job(
        RESOURCE_ID, "download-worker", NOW, timedelta(minutes=1)
    )
    recovered = await downloads.recover_stale_queued(NOW, NOW + timedelta(seconds=1))

    assert claimed is None
    assert recovered == ()


async def test_wrong_content_kind_and_owner_are_fail_closed(
    repositories: tuple[
        SqlAlchemyMediaImportRepository,
        SqlAlchemyDownloadRepository,
        async_sessionmaker,
    ],
) -> None:
    repository, _, _ = repositories
    await repository.create_resource(command(), now=NOW)

    assert (
        await repository.get_resource(RESOURCE_ID, OWNER_HASH, ContentKind.SCREENPLAY)
        is None
    )
    assert (
        await repository.get_resource(RESOURCE_ID, "e" * 64, ContentKind.VIDEO) is None
    )
    with pytest.raises(ImportPersistenceConflict):
        await repository.mark_verifying(
            RESOURCE_ID,
            OWNER_HASH,
            ContentKind.VIDEO,
            1,
            actual_size_bytes=DECLARED_SIZE,
            now=NOW,
        )
