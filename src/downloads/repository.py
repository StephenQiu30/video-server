"""Transactional PostgreSQL repository for media and download jobs."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.downloads.models import Artifact, DownloadJob
from src.downloads.state import JobStatus, assert_stage, assert_transition
from src.media.models import MediaFormat, MediaSource


def now_utc() -> datetime:
    return datetime.now(UTC)


class RepositoryConflict(RuntimeError):
    """Raised when a concurrent write changes the optimistic-lock version."""


class NotFoundError(LookupError):
    """Raised when an owner cannot access a resource."""


class DownloadRepository:
    """Small unit-of-work repository; callers own commit/rollback boundaries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _rowcount(result: object) -> int:
        return cast(CursorResult[Any], result).rowcount

    async def add_source(
        self,
        *,
        owner_token_hash: str,
        source_url: str,
        source_host: str,
        extractor_key: str,
        title: str,
        inspect_expires_at: datetime,
        external_id: str | None = None,
        thumbnail_url: str | None = None,
        duration_seconds: int | None = None,
        formats: Iterable[dict[str, object]] = (),
    ) -> MediaSource:
        source = MediaSource(
            owner_token_hash=owner_token_hash,
            source_url=source_url,
            source_host=source_host,
            extractor_key=extractor_key,
            external_id=external_id,
            title=title,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
            inspect_expires_at=inspect_expires_at,
        )
        # Attach through the relationship so SQLAlchemy assigns the generated
        # source UUID during flush instead of persisting a pre-flush ``None``.
        source.formats = [MediaFormat(**item) for item in formats]
        self.session.add(source)
        await self.session.flush()
        return source

    async def get_source(
        self, owner_token_hash: str, source_id: uuid.UUID
    ) -> MediaSource:
        source = await self.session.scalar(
            select(MediaSource)
            .where(
                MediaSource.id == source_id,
                MediaSource.owner_token_hash == owner_token_hash,
            )
            .options()
        )
        if source is None:
            raise NotFoundError("media source not found")
        return source

    async def add_job(
        self,
        *,
        owner_token_hash: str,
        client_request_id: uuid.UUID,
        source_id: uuid.UUID,
        format_id: uuid.UUID,
    ) -> DownloadJob:
        """Create a queued job, returning an idempotent replay when present."""
        existing = await self.session.scalar(
            select(DownloadJob).where(
                DownloadJob.owner_token_hash == owner_token_hash,
                DownloadJob.client_request_id == client_request_id,
            )
        )
        if existing is not None:
            if existing.source_id != source_id or existing.format_id != format_id:
                raise RepositoryConflict(
                    "client_request_id is already used for another download"
                )
            return existing

        source = await self.get_source(owner_token_hash, source_id)
        if source.inspect_expires_at <= now_utc():
            raise RepositoryConflict("media inspection has expired")
        fmt = await self.session.scalar(
            select(MediaFormat).where(
                MediaFormat.id == format_id, MediaFormat.source_id == source_id
            )
        )
        if fmt is None:
            raise NotFoundError("media format not found")

        job = DownloadJob(
            owner_token_hash=owner_token_hash,
            client_request_id=client_request_id,
            source_id=source_id,
            format_id=format_id,
            status=JobStatus.QUEUED.value,
            version=0,
        )
        self.session.add(job)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            replay = await self.session.scalar(
                select(DownloadJob).where(
                    DownloadJob.owner_token_hash == owner_token_hash,
                    DownloadJob.client_request_id == client_request_id,
                )
            )
            if replay is None:
                raise
            return replay
        return job

    async def get_job(
        self, owner_token_hash: str, job_id: uuid.UUID, *, lock: bool = False
    ) -> DownloadJob:
        query = (
            select(DownloadJob)
            .where(
                DownloadJob.id == job_id,
                DownloadJob.owner_token_hash == owner_token_hash,
            )
            .options(
                selectinload(DownloadJob.source),
                selectinload(DownloadJob.format),
                selectinload(DownloadJob.artifact),
            )
        )
        if lock:
            query = query.with_for_update()
        job = await self.session.scalar(query)
        if job is None:
            raise NotFoundError("download job not found")
        return job

    async def get_worker_job(
        self, job_id: uuid.UUID, *, lock: bool = True
    ) -> DownloadJob | None:
        query = (
            select(DownloadJob)
            .where(DownloadJob.id == job_id)
            .options(
                selectinload(DownloadJob.source),
                selectinload(DownloadJob.format),
                selectinload(DownloadJob.artifact),
            )
        )
        if lock:
            query = query.with_for_update()
        return cast(DownloadJob | None, await self.session.scalar(query))

    async def mark_published(
        self, job_id: uuid.UUID, published_at: datetime | None = None
    ) -> bool:
        published_at = published_at or now_utc()
        result = await self.session.execute(
            update(DownloadJob)
            .where(
                DownloadJob.id == job_id,
                DownloadJob.status == JobStatus.QUEUED.value,
                DownloadJob.published_at.is_(None),
            )
            .values(
                published_at=published_at,
                updated_at=published_at,
                version=DownloadJob.version + 1,
            )
        )
        return self._rowcount(result) == 1

    async def transition(
        self,
        job_id: uuid.UUID,
        *,
        expected: JobStatus | str,
        target: JobStatus | str,
        expected_version: int | None = None,
        stage: str | None = None,
        progress_percent: int | None = None,
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        at: datetime | None = None,
    ) -> DownloadJob:
        assert_transition(expected, target)
        assert_stage(stage)
        when = at or now_utc()
        conditions = [
            DownloadJob.id == job_id,
            DownloadJob.status == JobStatus(expected).value,
        ]
        if expected_version is not None:
            conditions.append(DownloadJob.version == expected_version)
        values: dict[str, object] = {
            "status": JobStatus(target).value,
            "updated_at": when,
            "version": DownloadJob.version + 1,
        }
        if stage is not None:
            values["stage"] = stage
        if progress_percent is not None:
            if not 0 <= progress_percent <= 100:
                raise ValueError("progress_percent must be between 0 and 100")
            values["progress_percent"] = progress_percent
        if downloaded_bytes is not None:
            values["downloaded_bytes"] = downloaded_bytes
        if total_bytes is not None:
            values["total_bytes"] = total_bytes
        if error_code is not None:
            values["error_code"] = error_code
        if error_message is not None:
            values["error_message"] = error_message
        if JobStatus(target) in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.EXPIRED,
        }:
            values["finished_at"] = when
            values["stage"] = None

        result = await self.session.execute(
            update(DownloadJob).where(*conditions).values(**values)
        )
        if self._rowcount(result) != 1:
            raise RepositoryConflict("download job status/version changed concurrently")
        await self.session.flush()
        job = await self.get_worker_job(job_id, lock=False)
        if job is None:
            raise NotFoundError("download job not found")
        if JobStatus(target) in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.EXPIRED,
        }:
            await self.session.execute(
                update(MediaSource)
                .where(MediaSource.id == job.source_id)
                .values(source_url=None)
            )
        return job

    async def touch_heartbeat(
        self, job_id: uuid.UUID, *, at: datetime | None = None
    ) -> bool:
        at = at or now_utc()
        result = await self.session.execute(
            update(DownloadJob)
            .where(
                DownloadJob.id == job_id, DownloadJob.status == JobStatus.RUNNING.value
            )
            .values(heartbeat_at=at, updated_at=at, version=DownloadJob.version + 1)
        )
        return self._rowcount(result) == 1

    async def update_progress(
        self,
        job_id: uuid.UUID,
        *,
        stage: str,
        progress_percent: int | None,
        downloaded_bytes: int | None = None,
        total_bytes: int | None = None,
        at: datetime | None = None,
    ) -> bool:
        assert_stage(stage)
        if progress_percent is not None and not 0 <= progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100")
        at = at or now_utc()
        values: dict[str, object] = {
            "stage": stage,
            "progress_percent": progress_percent,
            "updated_at": at,
            "heartbeat_at": at,
            "version": DownloadJob.version + 1,
        }
        if downloaded_bytes is not None:
            values["downloaded_bytes"] = downloaded_bytes
        if total_bytes is not None:
            values["total_bytes"] = total_bytes
        result = await self.session.execute(
            update(DownloadJob)
            .where(
                DownloadJob.id == job_id, DownloadJob.status == JobStatus.RUNNING.value
            )
            .values(**values)
        )
        return self._rowcount(result) == 1

    async def succeed_with_artifact(
        self,
        job_id: uuid.UUID,
        *,
        object_key: str,
        file_name: str,
        content_type: str,
        size_bytes: int,
        sha256: str,
        expires_at: datetime,
        at: datetime | None = None,
    ) -> Artifact:
        when = at or now_utc()
        job = await self.get_worker_job(job_id, lock=True)
        if job is None:
            raise NotFoundError("download job not found")
        if job.status != JobStatus.RUNNING.value:
            raise RepositoryConflict("only a running job can produce an artifact")
        artifact = Artifact(
            download_job_id=job_id,
            object_key=object_key,
            file_name=file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            expires_at=expires_at,
        )
        self.session.add(artifact)
        await self.session.flush()
        await self.session.execute(
            update(DownloadJob)
            .where(
                DownloadJob.id == job_id, DownloadJob.status == JobStatus.RUNNING.value
            )
            .values(
                status=JobStatus.SUCCEEDED.value,
                stage=None,
                progress_percent=100,
                finished_at=when,
                updated_at=when,
                version=DownloadJob.version + 1,
            )
        )
        await self.session.execute(
            update(MediaSource)
            .where(MediaSource.id == job.source_id)
            .values(source_url=None)
        )
        return artifact

    async def list_unpublished_jobs(self, *, limit: int = 100) -> list[DownloadJob]:
        result = await self.session.scalars(
            select(DownloadJob)
            .where(
                DownloadJob.status == JobStatus.QUEUED.value,
                DownloadJob.published_at.is_(None),
            )
            .order_by(DownloadJob.created_at)
            .limit(limit)
        )
        return list(result)

    async def collect_stale_running(
        self, *, stale_after: timedelta, at: datetime | None = None
    ) -> list[uuid.UUID]:
        at = at or now_utc()
        cutoff = at - stale_after
        result = await self.session.scalars(
            select(DownloadJob.id).where(
                DownloadJob.status == JobStatus.RUNNING.value,
                DownloadJob.heartbeat_at.is_not(None),
                DownloadJob.heartbeat_at < cutoff,
            )
        )
        ids = list(result)
        if ids:
            await self.session.execute(
                update(DownloadJob)
                .where(
                    DownloadJob.id.in_(ids),
                    DownloadJob.status == JobStatus.RUNNING.value,
                )
                .values(
                    status=JobStatus.FAILED.value,
                    error_code="worker_stale",
                    error_message="下载工作进程已失联",
                    finished_at=at,
                    updated_at=at,
                    stage=None,
                    version=DownloadJob.version + 1,
                )
            )
            await self.session.execute(
                update(MediaSource)
                .where(
                    MediaSource.id.in_(
                        select(DownloadJob.source_id).where(DownloadJob.id.in_(ids))
                    )
                )
                .values(source_url=None)
            )
        return ids

    async def expire_artifacts(self, *, at: datetime | None = None) -> list[str]:
        at = at or now_utc()
        rows = list(
            await self.session.scalars(
                select(Artifact)
                .where(Artifact.expires_at <= at, Artifact.deleted_at.is_(None))
                .with_for_update()
            )
        )
        keys = [row.object_key for row in rows]
        for artifact in rows:
            artifact.deleted_at = at
            await self.session.execute(
                update(DownloadJob)
                .where(
                    DownloadJob.id == artifact.download_job_id,
                    DownloadJob.status == JobStatus.SUCCEEDED.value,
                )
                .values(
                    status=JobStatus.EXPIRED.value,
                    finished_at=at,
                    updated_at=at,
                    version=DownloadJob.version + 1,
                )
            )
        return keys

    async def purge_metadata(self, *, older_than: datetime) -> int:
        result = await self.session.execute(
            delete(DownloadJob).where(
                DownloadJob.finished_at.is_not(None),
                DownloadJob.finished_at < older_than,
            )
        )
        return self._rowcount(result)
