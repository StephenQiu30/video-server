from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.analysis.models import (
    AnalysisArtifactSnapshot,
    AnalysisCreate,
    AnalysisJobSaveResult,
    AnalysisJobSnapshot,
    AnalysisPublish,
    AnalysisReportSnapshot,
    AnalysisRetry,
    AnalysisSkillView,
    AnalysisStoredReportFile,
)
from app.domain.analysis import AnalysisResult


class RequestFingerprinter(Protocol):
    def fingerprint(self, namespace: str, *values: str) -> str: ...


class AnalysisAvailability(Protocol):
    async def is_available(self, now: datetime) -> bool: ...


class AnalysisRepository(Protocol):
    async def get_artifact_for_download(
        self, download_id: UUID
    ) -> AnalysisArtifactSnapshot | None: ...

    async def create_job_and_enqueue(
        self, command: AnalysisCreate, *, now: datetime
    ) -> AnalysisJobSaveResult: ...

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None: ...

    async def get_latest_job_for_download(
        self, download_id: UUID, owner_hash: str
    ) -> AnalysisJobSnapshot | None: ...

    async def retry_job_and_enqueue(
        self, command: AnalysisRetry, *, now: datetime
    ) -> AnalysisJobSaveResult: ...

    async def get_result(self, job_id: UUID) -> AnalysisResult | None: ...

    async def get_latest_report(
        self, job_id: UUID
    ) -> AnalysisReportSnapshot | None: ...

    async def get_current_report_file(
        self, job_id: UUID, report_format: str
    ) -> AnalysisStoredReportFile | None: ...

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> AnalysisJobSnapshot: ...

    async def delete_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> bool: ...

    async def publish_result(self, command: AnalysisPublish) -> AnalysisJobSnapshot: ...


class AnalysisReportRenderer(Protocol):
    def render(self, markdown: str) -> bytes: ...


class AnalysisReportObjectReader(Protocol):
    async def read(self, object_key: str) -> bytes: ...


class AnalysisSkillCatalog(Protocol):
    def list(self) -> tuple[AnalysisSkillView, ...]: ...

    def resolve(self, skill_id: str) -> tuple[AnalysisSkillView, str] | None: ...
