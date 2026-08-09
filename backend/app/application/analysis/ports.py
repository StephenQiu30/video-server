from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.analysis.models import (
    AnalysisArtifactSnapshot,
    AnalysisCreate,
    AnalysisJobSaveResult,
    AnalysisJobSnapshot,
    AnalysisPublish,
)


class RequestFingerprinter(Protocol):
    def fingerprint(self, namespace: str, *values: str) -> str: ...


class AnalysisRepository(Protocol):
    async def get_artifact_for_download(
        self, download_id: UUID
    ) -> AnalysisArtifactSnapshot | None: ...

    async def create_job_and_enqueue(
        self, command: AnalysisCreate, *, now: datetime
    ) -> AnalysisJobSaveResult: ...

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None: ...

    async def get_result(self, job_id: UUID) -> dict[str, Any] | None: ...

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> AnalysisJobSnapshot: ...

    async def publish_result(self, command: AnalysisPublish) -> AnalysisJobSnapshot: ...
