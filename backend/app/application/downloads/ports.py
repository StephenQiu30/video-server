from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.downloads.download_models import (
    ArtifactSnapshot,
    DownloadCreate,
    JobSaveResult,
    JobSnapshot,
)
from app.application.downloads.inspection_models import (
    EncryptedUrl,
    InspectionCreate,
    InspectionSaveResult,
    InspectionSnapshot,
    RunnerInspection,
)


class UrlValidator(Protocol):
    def validate(self, url: str) -> str: ...


class UrlCipher(Protocol):
    def encrypt(self, url: str) -> EncryptedUrl: ...


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

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> JobSnapshot | None: ...

    async def get_artifact(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> ArtifactSnapshot | None: ...


class ObjectStorage(Protocol):
    async def presigned_download(self, object_key: str, *, ttl_seconds: int) -> str: ...
