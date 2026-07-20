"""Application-facing transaction helpers for download jobs.

HTTP handlers and the Worker can share this service without introducing a
second state store.  A caller supplies the SQLAlchemy session and commits the
transaction after each operation.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.downloads.models import Artifact, DownloadJob
from src.downloads.repository import DownloadRepository
from src.media.models import MediaSource


class DownloadService:
    def __init__(self, session: AsyncSession):
        self.repository = DownloadRepository(session)

    async def inspect_source(self, **kwargs: object) -> MediaSource:
        return await self.repository.add_source(**kwargs)  # type: ignore[arg-type]

    async def create_job(
        self,
        *,
        owner_token_hash: str,
        client_request_id: uuid.UUID,
        source_id: uuid.UUID,
        format_id: uuid.UUID,
    ) -> DownloadJob:
        return await self.repository.add_job(
            owner_token_hash=owner_token_hash,
            client_request_id=client_request_id,
            source_id=source_id,
            format_id=format_id,
        )

    async def transition(self, job_id: uuid.UUID, **kwargs: object) -> DownloadJob:
        return await self.repository.transition(job_id, **kwargs)  # type: ignore[arg-type]

    async def succeed(self, job_id: uuid.UUID, **kwargs: object) -> Artifact:
        return await self.repository.succeed_with_artifact(job_id, **kwargs)  # type: ignore[arg-type]
