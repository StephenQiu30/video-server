from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.imports import (
    ImportPersistenceIdempotencyConflict,
    ImportResourceCreate,
)
from app.application.imports.events import CONTENT_IMPORT_VERIFY_REQUESTED
from app.domain.imports import ContentKind, ImportSourceFormat, ImportStatus
from app.infrastructure.database import Base, SqlAlchemyDocumentImportRepository
from app.infrastructure.database.models import (
    DocumentImportAttemptRow,
    DocumentRow,
    DownloadJobRow,
    OutboxEventRow,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
RESOURCE_ID = UUID("33333333-3333-4333-8333-333333333333")
SECOND_ID = UUID("44444444-4444-4444-8444-444444444444")
OWNER_HASH = "a" * 64
DECLARED_SIZE = 5 * 1024**2 + 1


@pytest.fixture
async def repository_data():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    yield SqlAlchemyDocumentImportRepository(sessions), sessions
    await engine.dispose()


def command(
    *,
    resource_id: UUID = RESOURCE_ID,
    fingerprint: str = "b" * 64,
) -> ImportResourceCreate:
    return ImportResourceCreate(
        id=resource_id,
        owner_hash=OWNER_HASH,
        idempotency_key="document-1",
        request_fingerprint=fingerprint,
        content_kind=ContentKind.SCREENPLAY,
        source_format=ImportSourceFormat.FOUNTAIN,
        display_name="example.fountain",
        content_type=ImportSourceFormat.FOUNTAIN.content_type,
        declared_size_bytes=DECLARED_SIZE,
        declared_sha256="c" * 64,
        rights_statement_version="content-rights-v1",
    )


async def test_create_is_owned_idempotent_and_has_no_download_projection(
    repository_data,
) -> None:
    repository, sessions = repository_data

    created = await repository.create_resource(command(), now=NOW)
    replay = await repository.create_resource(
        command(resource_id=SECOND_ID), now=NOW + timedelta(seconds=1)
    )

    assert created.created is True
    assert replay.created is False
    assert replay.resource.id == RESOURCE_ID
    assert replay.resource.content_kind == ContentKind.SCREENPLAY.value
    async with sessions() as session:
        stored = await session.get(DocumentRow, RESOURCE_ID)
        download = await session.get(DownloadJobRow, RESOURCE_ID)
        outbox_count = await session.scalar(select(func.count(OutboxEventRow.id)))
    assert stored is not None
    assert stored.title == "example"
    assert stored.quality_warnings == []
    assert download is None
    assert outbox_count == 0


async def test_create_rejects_reused_key_with_another_fingerprint(
    repository_data,
) -> None:
    repository, _ = repository_data
    await repository.create_resource(command(), now=NOW)

    with pytest.raises(ImportPersistenceIdempotencyConflict):
        await repository.create_resource(
            command(resource_id=SECOND_ID, fingerprint="d" * 64), now=NOW
        )


async def test_owner_and_content_kind_are_fail_closed(repository_data) -> None:
    repository, _ = repository_data
    await repository.create_resource(command(), now=NOW)

    assert (
        await repository.get_resource(RESOURCE_ID, OWNER_HASH, ContentKind.VIDEO)
        is None
    )
    assert (
        await repository.get_resource(RESOURCE_ID, "e" * 64, ContentKind.SCREENPLAY)
        is None
    )


async def activated_document(repository):
    await repository.create_resource(command(), now=NOW)
    begun = await repository.begin_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.SCREENPLAY,
        part_size_bytes=5 * 1024**2,
        part_count=2,
        expires_at=NOW + timedelta(minutes=15),
        now=NOW,
    )
    await repository.activate_upload_attempt(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.SCREENPLAY,
        begun.attempt.attempt,
        upload_id="document-upload-1",
        now=NOW,
    )
    return begun.attempt


async def test_complete_handoff_writes_one_screenplay_outbox_event(
    repository_data,
) -> None:
    repository, sessions = repository_data
    attempt = await activated_document(repository)

    verifying = await repository.mark_verifying(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.SCREENPLAY,
        attempt.attempt,
        actual_size_bytes=DECLARED_SIZE,
        now=NOW + timedelta(seconds=1),
    )
    replay = await repository.mark_verifying(
        RESOURCE_ID,
        OWNER_HASH,
        ContentKind.SCREENPLAY,
        attempt.attempt,
        actual_size_bytes=DECLARED_SIZE,
        now=NOW + timedelta(seconds=2),
    )

    assert verifying.status == ImportStatus.VERIFYING.value
    assert replay.version == verifying.version
    async with sessions() as session:
        events = (
            await session.scalars(
                select(OutboxEventRow).where(
                    OutboxEventRow.event_type == CONTENT_IMPORT_VERIFY_REQUESTED
                )
            )
        ).all()
    assert len(events) == 1
    assert events[0].aggregate_type == "document"
    assert events[0].payload["content_kind"] == ContentKind.SCREENPLAY.value


async def test_cancel_is_idempotent_and_returns_quarantine_cleanup(
    repository_data,
) -> None:
    repository, sessions = repository_data
    attempt = await activated_document(repository)

    cancelled = await repository.cancel_resource(
        RESOURCE_ID, OWNER_HASH, ContentKind.SCREENPLAY, now=NOW
    )
    replay = await repository.cancel_resource(
        RESOURCE_ID, OWNER_HASH, ContentKind.SCREENPLAY, now=NOW
    )

    assert cancelled.resource.status == ImportStatus.CANCELLED.value
    assert replay.resource.version == cancelled.resource.version
    assert cancelled.cleanup == replay.cleanup
    assert len(cancelled.cleanup) == 1
    async with sessions() as session:
        stored = await session.get(
            DocumentImportAttemptRow, (RESOURCE_ID, attempt.attempt)
        )
    assert stored is not None
    assert stored.status == ImportStatus.CANCELLED.value
