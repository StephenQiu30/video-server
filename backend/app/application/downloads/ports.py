from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.downloads.analytics_models import DownloadAnalyticsSnapshot
from app.application.downloads.download_models import (
    ArtifactSnapshot,
    DownloadCreate,
    JobSaveResult,
    JobSnapshot,
)
from app.application.downloads.history_models import DownloadHistoryPageSnapshot
from app.application.downloads.inspection_models import (
    EncryptedUrl,
    InspectionCreate,
    InspectionSaveResult,
    InspectionSnapshot,
    RetrySourceSnapshot,
    RunnerInspection,
)


class UrlValidator(Protocol):
    def validate(self, url: str) -> str: ...


class UrlCipher(Protocol):
    def encrypt(self, url: str) -> EncryptedUrl: ...

    def decrypt(self, envelope: EncryptedUrl) -> str: ...


class MediaRunner(Protocol):
    async def inspect(self, url: str) -> RunnerInspection: ...


class RequestFingerprinter(Protocol):
    def fingerprint(self, namespace: str, *values: str) -> str: ...


class DownloadRepository(Protocol):
    async def save_inspection(
        self, command: InspectionCreate
    ) -> InspectionSaveResult: ...

    async def get_inspection(
        self, inspection_id: UUID, owner_hash: str, now: datetime
    ) -> InspectionSnapshot | None: ...

    async def create_job(
        self, command: DownloadCreate, *, now: datetime
    ) -> JobSaveResult: ...

    async def get_job(self, job_id: UUID) -> JobSnapshot | None: ...

    async def get_retry_source(
        self, job_id: UUID, owner_hash: str
    ) -> RetrySourceSnapshot | None: ...

    async def list_download_history(
        self,
        owner_hash: str,
        *,
        page: int,
        page_size: int,
        status: str | None,
        search: str | None,
        now: datetime,
    ) -> DownloadHistoryPageSnapshot: ...

    async def get_download_analytics(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> DownloadAnalyticsSnapshot: ...

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> JobSnapshot | None: ...

    async def get_artifact(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> ArtifactSnapshot | None: ...


class ObjectStorage(Protocol):
    async def presigned_download(
        self, object_key: str, *, title: str | None = None, ttl_seconds: int
    ) -> str: ...
