from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.application.downloads import (
    ApplicationError,
    ApplicationErrorCode,
    ArtifactSnapshot,
    CancelDownload,
    CreateDownload,
    FormatSnapshot,
    GetDownload,
    HmacRequestFingerprinter,
    InspectionSnapshot,
    IssueDownloadUrl,
    RetryDownload,
    plan_to_documents,
)
from app.domain.downloads import DownloadStatus
from tests.unit.application.fakes import FakeRepository, FakeStorage
from tests.unit.application.test_inspect_media import NOW, OWNER, plan


def seed_inspection(
    repository: FakeRepository,
    *,
    owner: str = OWNER,
    expires_at: datetime | None = None,
) -> tuple[UUID, UUID]:
    inspection_id, format_id = uuid4(), uuid4()
    semantic, hints = plan_to_documents(plan())
    repository.inspections[inspection_id] = InspectionSnapshot(
        id=inspection_id,
        owner_hash=owner,
        request_fingerprint="a" * 64,
        extractor_key="Controlled",
        provider_media_id="video-1",
        title="Owned video",
        duration_seconds=30,
        metadata={},
        expires_at=expires_at or NOW + timedelta(minutes=15),
        formats=(
            FormatSnapshot(
                id=format_id,
                display_name="1080p MP4",
                plan_fingerprint="b" * 64,
                semantic_plan=semantic,
                provider_hints=hints,
                expires_at=expires_at or NOW + timedelta(minutes=15),
            ),
        ),
    )
    return inspection_id, format_id


def creator(repository: FakeRepository) -> CreateDownload:
    return CreateDownload(
        repository=repository,
        fingerprinter=HmacRequestFingerprinter(b"k" * 32),
        now=lambda: NOW,
        new_id=uuid4,
        max_attempts=3,
    )


def retrier(repository: FakeRepository) -> RetryDownload:
    return RetryDownload(
        repository=repository,
        fingerprinter=HmacRequestFingerprinter(b"k" * 32),
        now=lambda: NOW,
        new_id=uuid4,
        max_attempts=3,
    )


@pytest.mark.asyncio
async def test_create_download_persists_job_and_outbox_idempotently() -> None:
    repository = FakeRepository()
    inspection_id, format_id = seed_inspection(repository)
    create = creator(repository)

    first = await create(inspection_id, format_id, OWNER, "download-1")
    replay = await create(inspection_id, format_id, OWNER, "download-1")

    assert first.id == replay.id
    assert first.status is DownloadStatus.QUEUED
    assert repository.outbox_events == 1
    command = repository.download_commands[0]
    assert command.semantic_plan["height"] == 1080
    assert "hints" not in command.semantic_plan


@pytest.mark.asyncio
async def test_create_rejects_owner_mismatch_expiry_and_idempotency_conflict() -> None:
    repository = FakeRepository()
    foreign_id, foreign_format = seed_inspection(repository, owner="b" * 64)
    expired_id, expired_format = seed_inspection(
        repository, expires_at=NOW - timedelta(seconds=1)
    )
    create = creator(repository)

    with pytest.raises(ApplicationError) as foreign:
        await create(foreign_id, foreign_format, OWNER, "foreign")
    assert foreign.value.code is ApplicationErrorCode.NOT_FOUND

    with pytest.raises(ApplicationError) as expired:
        await create(expired_id, expired_format, OWNER, "expired")
    assert expired.value.code is ApplicationErrorCode.RESOURCE_EXPIRED

    format_expired_id, format_expired = seed_inspection(repository)
    source = repository.inspections[format_expired_id]
    repository.inspections[format_expired_id] = replace(
        source,
        formats=(replace(source.formats[0], expires_at=NOW),),
    )
    with pytest.raises(ApplicationError) as expired_selection:
        await create(format_expired_id, format_expired, OWNER, "format-expired")
    assert expired_selection.value.code is ApplicationErrorCode.RESOURCE_EXPIRED

    first_id, first_format = seed_inspection(repository)
    other_id, other_format = seed_inspection(repository)
    await create(first_id, first_format, OWNER, "same")
    with pytest.raises(ApplicationError) as conflict:
        await create(other_id, other_format, OWNER, "same")
    assert conflict.value.code is ApplicationErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.asyncio
async def test_get_and_cancel_enforce_owner_and_status() -> None:
    repository = FakeRepository()
    inspection_id, format_id = seed_inspection(repository)
    created = await creator(repository)(inspection_id, format_id, OWNER, "download-1")

    with pytest.raises(ApplicationError) as foreign:
        await GetDownload(repository)(created.id, "b" * 64)
    assert foreign.value.code is ApplicationErrorCode.NOT_FOUND

    cancelled = await CancelDownload(repository, now=lambda: NOW)(created.id, OWNER)
    assert cancelled.status is DownloadStatus.CANCELLED
    with pytest.raises(ApplicationError) as terminal:
        await CancelDownload(repository, now=lambda: NOW)(created.id, OWNER)
    assert terminal.value.code is ApplicationErrorCode.INVALID_STATE


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_status", ["failed", "cancelled"])
async def test_retry_creates_a_new_job_and_preserves_terminal_history(
    terminal_status: str,
) -> None:
    repository = FakeRepository()
    inspection_id, format_id = seed_inspection(repository)
    original = await creator(repository)(inspection_id, format_id, OWNER, "original")
    repository.jobs[original.id] = replace(
        repository.jobs[original.id],
        status=terminal_status,
        attempt=3,
        finished_at=NOW,
    )

    retried = await retrier(repository)(original.id, OWNER, "manual-retry")
    replay = await retrier(repository)(original.id, OWNER, "manual-retry")

    assert retried.id != original.id
    assert replay.id == retried.id
    assert retried.status is DownloadStatus.QUEUED
    assert retried.attempt == 0
    assert repository.jobs[original.id].status == terminal_status
    assert repository.outbox_events == 2


@pytest.mark.asyncio
async def test_retry_rejects_active_successful_and_foreign_jobs() -> None:
    repository = FakeRepository()
    inspection_id, format_id = seed_inspection(repository)
    original = await creator(repository)(inspection_id, format_id, OWNER, "original")
    retry = retrier(repository)

    for status in ("queued", "running", "retry_wait", "succeeded"):
        repository.jobs[original.id] = replace(
            repository.jobs[original.id], status=status
        )
        with pytest.raises(ApplicationError) as invalid:
            await retry(original.id, OWNER, f"retry-{status}")
        assert invalid.value.code is ApplicationErrorCode.INVALID_STATE

    repository.jobs[original.id] = replace(
        repository.jobs[original.id], status="failed"
    )
    with pytest.raises(ApplicationError) as foreign:
        await retry(original.id, "b" * 64, "retry-foreign")
    assert foreign.value.code is ApplicationErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_retry_rejects_an_expired_source_inspection() -> None:
    repository = FakeRepository()
    inspection_id, format_id = seed_inspection(repository)
    original = await creator(repository)(inspection_id, format_id, OWNER, "original")
    repository.jobs[original.id] = replace(
        repository.jobs[original.id], status="failed", finished_at=NOW
    )
    repository.inspections[inspection_id] = replace(
        repository.inspections[inspection_id], expires_at=NOW
    )

    with pytest.raises(ApplicationError) as expired:
        await retrier(repository)(original.id, OWNER, "retry-expired")

    assert expired.value.code is ApplicationErrorCode.RESOURCE_EXPIRED


@pytest.mark.asyncio
async def test_download_url_requires_success_and_unexpired_artifact() -> None:
    repository, storage = FakeRepository(), FakeStorage()
    inspection_id, format_id = seed_inspection(repository)
    created = await creator(repository)(inspection_id, format_id, OWNER, "download-1")
    issue = IssueDownloadUrl(
        repository, storage, now=lambda: NOW, url_ttl=timedelta(minutes=5)
    )

    with pytest.raises(ApplicationError) as pending:
        await issue(created.id, OWNER)
    assert pending.value.code is ApplicationErrorCode.DOWNLOAD_NOT_READY

    repository.jobs[created.id] = replace(
        repository.jobs[created.id], status="succeeded", progress=100
    )
    repository.artifacts[created.id] = ArtifactSnapshot(
        id=uuid4(),
        job_id=created.id,
        attempt=1,
        bucket="video-artifacts",
        object_key=f"downloads/{created.id}/1/video.mp4",
        sha256="d" * 64,
        size_bytes=1_024,
        duration_ms=30_000,
        container="mp4",
        content_type="video/mp4",
        media_metadata={},
        expires_at=NOW + timedelta(seconds=90),
    )
    result = await issue(created.id, OWNER)

    assert result.url == "https://objects.example/download-token"
    assert result.expires_at == NOW + timedelta(seconds=90)
    assert storage.calls == [(f"downloads/{created.id}/1/video.mp4", 90)]

    repository.artifacts[created.id] = replace(
        repository.artifacts[created.id], expires_at=NOW
    )
    with pytest.raises(ApplicationError) as expired:
        await issue(created.id, OWNER)
    assert expired.value.code is ApplicationErrorCode.RESOURCE_EXPIRED
