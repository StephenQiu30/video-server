from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.infrastructure.database.models import (
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaImportRow,
    MediaInspectionRow,
)

START = datetime(2026, 8, 4, tzinfo=UTC)
END = datetime(2026, 8, 11, tzinfo=UTC)


async def add_job(
    sessions,
    *,
    extractor: str,
    owner: str,
    status: str,
    created_at: datetime,
    duration: int,
    size_bytes: int = 0,
    source_expires_at: datetime | None = None,
) -> None:
    inspection_id, format_id, job_id = uuid4(), uuid4(), uuid4()
    expires_at = source_expires_at or END + timedelta(days=1)
    async with sessions.begin() as session:
        session.add(
            MediaInspectionRow(
                id=inspection_id,
                owner_hash=owner,
                idempotency_key=f"inspection-{inspection_id}",
                request_fingerprint="a" * 64,
                url_ciphertext=b"encrypted",
                url_nonce=b"nonce",
                url_key_id="primary",
                extractor_key=extractor,
                provider_media_id=f"media-{inspection_id}",
                title="Analytics video",
                duration_seconds=duration,
                metadata_json={},
                expires_at=expires_at,
                created_at=created_at,
            )
        )
        await session.flush()
        session.add(
            MediaFormatRow(
                id=format_id,
                inspection_id=inspection_id,
                display_name="720p MP4",
                plan_fingerprint="b" * 64,
                semantic_plan={"height": 720},
                provider_hints={},
                expires_at=expires_at,
                created_at=created_at,
            )
        )
        await session.flush()
        session.add(
            DownloadJobRow(
                id=job_id,
                inspection_id=inspection_id,
                format_id=format_id,
                owner_hash=owner,
                idempotency_key=f"download-{job_id}",
                request_fingerprint="c" * 64,
                semantic_plan={"height": 720},
                status=status,
                progress=100 if status == "succeeded" else 0,
                attempt=1 if status in {"succeeded", "failed"} else 0,
                finished_at=(
                    created_at + timedelta(minutes=1)
                    if status in {"succeeded", "failed", "cancelled"}
                    else None
                ),
                created_at=created_at,
                updated_at=created_at,
            )
        )
        await session.flush()
        if size_bytes:
            session.add(
                ArtifactRow(
                    id=uuid4(),
                    job_id=job_id,
                    attempt=1,
                    bucket="video-artifacts",
                    object_key=f"downloads/{job_id}/1/video.mp4",
                    sha256="d" * 64,
                    size_bytes=size_bytes,
                    duration_ms=duration * 1000,
                    container="mp4",
                    content_type="video/mp4",
                    media_metadata={},
                    expires_at=expires_at,
                    created_at=created_at,
                )
            )


async def add_browser_import(
    sessions,
    *,
    owner: str,
    created_at: datetime,
    duration_ms: int,
    size_bytes: int,
) -> None:
    job_id = uuid4()
    expires_at = END + timedelta(days=1)
    async with sessions.begin() as session:
        session.add(
            DownloadJobRow(
                id=job_id,
                source_kind="browser_import",
                inspection_id=None,
                format_id=None,
                owner_hash=owner,
                idempotency_key=f"import-job-{job_id}",
                request_fingerprint="e" * 64,
                semantic_plan={"container": "mp4"},
                status="succeeded",
                progress=100,
                attempt=1,
                finished_at=created_at + timedelta(minutes=1),
                created_at=created_at,
                updated_at=created_at,
            )
        )
        await session.flush()
        session.add(
            MediaImportRow(
                id=job_id,
                owner_hash=owner,
                idempotency_key=f"import-{job_id}",
                request_fingerprint="f" * 64,
                source_format="mp4",
                display_name="Local sample.mp4",
                content_type="video/mp4",
                declared_size_bytes=size_bytes,
                declared_sha256="1" * 64,
                rights_statement_version="v1",
                status="ready",
                attempt=1,
                finished_at=created_at + timedelta(minutes=1),
                created_at=created_at,
                updated_at=created_at,
            )
        )
        session.add(
            ArtifactRow(
                id=uuid4(),
                job_id=job_id,
                attempt=1,
                bucket="video-artifacts",
                object_key=f"imports/{job_id}/video.mp4",
                sha256="1" * 64,
                size_bytes=size_bytes,
                duration_ms=duration_ms,
                container="mp4",
                content_type="video/mp4",
                media_metadata={},
                expires_at=expires_at,
                created_at=created_at,
            )
        )
