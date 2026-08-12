from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.application import downloads as application
from app.infrastructure import database
from app.infrastructure.download_store import SqlAlchemyDownloadStore
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

NOW = datetime(2026, 8, 6, tzinfo=UTC)


@pytest.mark.asyncio
async def test_download_store_maps_the_complete_application_lifecycle() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(database.Base.metadata.create_all)
    repository = database.SqlAlchemyDownloadRepository(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    store = SqlAlchemyDownloadStore(repository)
    inspection_id, format_id = uuid4(), uuid4()
    owner = "a" * 64
    expires = NOW + timedelta(hours=1)

    saved = await store.save_inspection(
        application.InspectionCreate(
            id=inspection_id,
            owner_hash=owner,
            idempotency_key="inspect-1",
            request_fingerprint="f" * 64,
            url_ciphertext=b"encrypted",
            url_nonce=b"n" * 16,
            url_key_id="fernet-v1",
            extractor_key="Example",
            provider_media_id="media-1",
            title="Controlled sample",
            duration_seconds=10,
            metadata={"thumbnail_url": "data:image/avif;base64,Y292ZXI="},
            expires_at=expires,
            formats=(
                application.FormatCreate(
                    id=format_id,
                    display_name="720p MP4",
                    plan_fingerprint="p" * 64,
                    semantic_plan={"height": 720},
                    provider_hints={"video_id": "v1"},
                    expires_at=expires,
                ),
            ),
        )
    )
    loaded = await store.get_inspection(inspection_id, owner, NOW)
    job_id = uuid4()
    created = await store.create_job(
        application.DownloadCreate(
            id=job_id,
            inspection_id=inspection_id,
            format_id=format_id,
            owner_hash=owner,
            idempotency_key="download-1",
            request_fingerprint="d" * 64,
            semantic_plan={"height": 720},
        ),
        now=NOW,
    )

    assert saved.created is True
    assert loaded.formats[0].display_name == "720p MP4"
    assert created.job.id == job_id
    assert (await store.get_job(job_id)).status == "queued"
    history = await store.list_download_history(
        owner,
        page=1,
        page_size=20,
        status="queued",
        search="Controlled",
        now=NOW,
    )
    assert history.total == 1
    assert history.items[0].title == "Controlled sample"
    assert history.items[0].thumbnail_url == "data:image/avif;base64,Y292ZXI="
    assert history.summary.active == 1
    other_owner = await store.list_download_history(
        "b" * 64,
        page=1,
        page_size=20,
        status=None,
        search=None,
        now=NOW,
    )
    assert other_owner.total == 0

    claimed = await repository.claim_job(
        job_id,
        "worker-1",
        NOW,
        timedelta(minutes=1),
    )
    assert claimed is not None
    await repository.heartbeat(
        job_id,
        "worker-1",
        claimed.attempt,
        stage="uploading",
        stage_rank=5,
        progress=95,
        now=NOW + timedelta(seconds=1),
        lease_for=timedelta(minutes=1),
    )
    await repository.complete_success(
        job_id,
        "worker-1",
        claimed.attempt,
        database.ArtifactCreate(
            bucket="video-artifacts",
            sha256="0" * 64,
            size_bytes=1024,
            duration_ms=10_000,
            container="mp4",
            content_type="video/mp4",
            media_metadata={},
            expires_at=expires,
        ),
        now=NOW + timedelta(seconds=2),
    )
    artifact = await store.get_artifact(job_id, owner, NOW)

    assert artifact.object_key.endswith("/video.mp4")
    assert (await store.get_job(job_id)).status == "succeeded"
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        inspection = await session.get(database.MediaInspectionRow, inspection_id)
        assert inspection is not None
        inspection.expires_at = NOW - timedelta(minutes=1)
        await session.commit()
    expired_source_history = await store.list_download_history(
        owner,
        page=1,
        page_size=20,
        status="succeeded",
        search="Controlled",
        now=NOW,
    )
    assert expired_source_history.items[0].title == "Controlled sample"
    assert expired_source_history.items[0].file_available is True
    assert expired_source_history.items[0].file_expires_at == expires
    retry_source = await store.get_retry_source(job_id, owner)
    assert retry_source.encrypted_url.ciphertext == b"encrypted"

    expired_file_history = await store.list_download_history(
        owner,
        page=1,
        page_size=20,
        status="succeeded",
        search="Controlled",
        now=expires,
    )
    assert expired_file_history.items[0].file_available is False
    await engine.dispose()


@pytest.mark.asyncio
async def test_download_store_maps_cancellation() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(database.Base.metadata.create_all)
    repository = database.SqlAlchemyDownloadRepository(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    store = SqlAlchemyDownloadStore(repository)
    inspection_id, format_id, job_id = uuid4(), uuid4(), uuid4()
    owner = "b" * 64
    expires = NOW + timedelta(hours=1)
    await store.save_inspection(
        application.InspectionCreate(
            id=inspection_id,
            owner_hash=owner,
            idempotency_key="inspect-cancel",
            request_fingerprint="i" * 64,
            url_ciphertext=b"encrypted",
            url_nonce=b"n" * 16,
            url_key_id="fernet-v1",
            extractor_key="Example",
            provider_media_id="media-2",
            title="Controlled sample",
            duration_seconds=10,
            metadata={},
            expires_at=expires,
            formats=(
                application.FormatCreate(
                    id=format_id,
                    display_name="720p MP4",
                    plan_fingerprint="p" * 64,
                    semantic_plan={"height": 720},
                    provider_hints={},
                    expires_at=expires,
                ),
            ),
        )
    )
    await store.create_job(
        application.DownloadCreate(
            id=job_id,
            inspection_id=inspection_id,
            format_id=format_id,
            owner_hash=owner,
            idempotency_key="download-cancel",
            request_fingerprint="d" * 64,
            semantic_plan={"height": 720},
        ),
        now=NOW,
    )

    cancelled = await store.cancel_job(job_id, owner, NOW)

    assert cancelled.status == "cancelled"
    await engine.dispose()
