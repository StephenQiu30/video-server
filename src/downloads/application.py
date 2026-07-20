"""HTTP-facing application service for jobs and private artifact URLs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from src.core.errors import AppError
from src.downloads.models import DownloadJob
from src.downloads.repository import DownloadRepository


class DownloadApplicationService:
    def __init__(self, session_factory: Any, storage: Any, settings: Any) -> None:
        self.session_factory = session_factory
        self.storage = storage
        self.settings = settings

    async def create_download(
        self,
        *,
        owner_token_hash: str,
        source_id: uuid.UUID,
        format_id: uuid.UUID,
        client_request_id: uuid.UUID,
    ) -> tuple[Any, bool]:
        async with self.session_factory() as session:
            existing = await session.scalar(
                select(DownloadJob).where(
                    DownloadJob.owner_token_hash == owner_token_hash,
                    DownloadJob.client_request_id == client_request_id,
                )
            )
            if existing is not None:
                if existing.source_id != source_id or existing.format_id != format_id:
                    raise AppError(
                        "IDEMPOTENCY_CONFLICT",
                        "The client request id conflicts with an existing download.",
                        status_code=409,
                    )
                return existing, False
            repository = DownloadRepository(session)
            try:
                job = await repository.add_job(
                    owner_token_hash=owner_token_hash,
                    client_request_id=client_request_id,
                    source_id=source_id,
                    format_id=format_id,
                )
            except Exception as exc:
                message = str(exc).lower()
                if "expired" in message:
                    raise AppError(
                        "INSPECTION_EXPIRED",
                        "The media inspection has expired.",
                        status_code=410,
                    ) from exc
                raise
            await session.commit()
            return job, True

    async def get_download(self, *, owner_token_hash: str, job_id: uuid.UUID) -> Any:
        async with self.session_factory() as session:
            repository = DownloadRepository(session)
            try:
                return await repository.get_job(owner_token_hash, job_id)
            except LookupError as exc:
                raise AppError(
                    "RESOURCE_NOT_FOUND",
                    "The requested download was not found.",
                    status_code=404,
                ) from exc

    async def create_download_url(
        self, *, owner_token_hash: str, job_id: uuid.UUID
    ) -> dict[str, Any]:
        async with self.session_factory() as session:
            repository = DownloadRepository(session)
            try:
                job = await repository.get_job(owner_token_hash, job_id)
            except LookupError as exc:
                raise AppError(
                    "RESOURCE_NOT_FOUND",
                    "The requested download was not found.",
                    status_code=404,
                ) from exc
            if job.status == "expired":
                raise AppError(
                    "JOB_EXPIRED", "The download file has expired.", status_code=410
                )
            if job.status != "succeeded" or job.artifact is None:
                raise AppError(
                    "JOB_NOT_READY", "The download is not ready yet.", status_code=409
                )
            now = datetime.now(UTC)
            if job.artifact.deleted_at is not None or job.artifact.expires_at <= now:
                raise AppError(
                    "JOB_EXPIRED", "The download file has expired.", status_code=410
                )
            ttl = min(
                int(self.settings.minio_presigned_url_ttl_seconds),
                max(1, int((job.artifact.expires_at - now).total_seconds())),
            )
            url = await self.storage.presigned_download(
                job.artifact.object_key,
                expires_seconds=ttl,
                response_filename=job.artifact.file_name,
            )
            return {
                "url": url,
                "expires_at": now + timedelta(seconds=ttl),
                "file_name": job.artifact.file_name,
            }


__all__ = ["DownloadApplicationService"]
