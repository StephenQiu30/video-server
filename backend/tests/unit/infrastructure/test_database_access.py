from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.infrastructure.database import (
    Base,
    DownloadCreate,
    FormatCreate,
    InspectionCreate,
    RepositoryNotFound,
    SqlAlchemyDownloadRepository,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def repository() -> SqlAlchemyDownloadRepository:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield SqlAlchemyDownloadRepository(factory)
    await engine.dispose()


def _inspection(inspection_id, format_id, now) -> InspectionCreate:
    return InspectionCreate(
        id=inspection_id,
        owner_hash="a" * 64,
        idempotency_key="inspect-key",
        request_fingerprint="b" * 64,
        url_ciphertext=b"cipher",
        url_nonce=b"nonce",
        url_key_id="primary",
        extractor_key="Youtube",
        provider_media_id="controlled",
        title="Controlled video",
        duration_seconds=30,
        metadata={},
        expires_at=now + timedelta(minutes=15),
        formats=(
            FormatCreate(
                id=format_id,
                display_name="720p",
                plan_fingerprint="c" * 64,
                semantic_plan={"height": 720},
                provider_hints={},
                expires_at=now + timedelta(minutes=15),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_inspection_idempotency_owner_and_ttl(repository) -> None:
    now = datetime.now(UTC)
    inspection_id, format_id = uuid4(), uuid4()
    first = await repository.save_inspection(_inspection(inspection_id, format_id, now))
    replay = await repository.save_inspection(_inspection(uuid4(), uuid4(), now))
    assert first.created is True
    assert replay.created is False
    assert replay.inspection.id == inspection_id
    assert (
        len((await repository.get_inspection(inspection_id, "a" * 64, now)).formats)
        == 1
    )
    with pytest.raises(RepositoryNotFound):
        await repository.get_inspection(inspection_id, "x" * 64, now)
    with pytest.raises(RepositoryNotFound):
        await repository.get_inspection(
            inspection_id, "a" * 64, now + timedelta(minutes=16)
        )


@pytest.mark.asyncio
async def test_cancel_running_job_revokes_worker_lease(repository) -> None:
    now = datetime.now(UTC)
    inspection_id, format_id, job_id = uuid4(), uuid4(), uuid4()
    await repository.save_inspection(_inspection(inspection_id, format_id, now))
    await repository.create_job(
        DownloadCreate(
            id=job_id,
            inspection_id=inspection_id,
            format_id=format_id,
            owner_hash="a" * 64,
            idempotency_key="download-key",
            request_fingerprint="d" * 64,
            semantic_plan={"height": 720},
        ),
        now=now,
    )
    await repository.claim_job(job_id, "worker", now, timedelta(seconds=60))
    cancelled = await repository.cancel_job(
        job_id, "a" * 64, now + timedelta(seconds=1)
    )
    assert (cancelled.status, cancelled.error_code) == ("cancelled", "cancelled")
    assert not await repository.heartbeat(
        job_id,
        "worker",
        1,
        stage="downloading",
        stage_rank=2,
        progress=10,
        now=now + timedelta(seconds=2),
        lease_for=timedelta(seconds=60),
    )
