from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.application.downloads import EncryptedUrl
from app.domain.downloads import DownloadPlan, DownloadStage

from .models import ArtifactDetails


class JobState(Protocol):
    @property
    def status(self) -> str: ...

    @property
    def attempt(self) -> int: ...

    @property
    def lease_owner(self) -> str | None: ...

    @property
    def lease_expires_at(self) -> datetime | None: ...


class JobSource(Protocol):
    @property
    def semantic_plan(self) -> dict[str, object]: ...

    @property
    def provider_hints(self) -> dict[str, object]: ...

    @property
    def extractor_key(self) -> str: ...

    @property
    def provider_media_id(self) -> str: ...

    @property
    def url_ciphertext(self) -> bytes: ...

    @property
    def url_nonce(self) -> bytes: ...

    @property
    def url_key_id(self) -> str: ...


class RunnerArtifactView(Protocol):
    @property
    def task_id(self) -> str: ...

    @property
    def workspace(self) -> Path: ...

    @property
    def artifact(self) -> Path: ...

    @property
    def size_bytes(self) -> int: ...

    @property
    def sha256(self) -> str: ...

    @property
    def duration_seconds(self) -> float: ...

    @property
    def container(self) -> str: ...

    @property
    def video_streams(self) -> int: ...

    @property
    def audio_streams(self) -> int: ...


class RunnerProgressView(Protocol):
    @property
    def stage(self) -> DownloadStage: ...

    @property
    def progress(self) -> int: ...


class ExecutionRepository(Protocol):
    async def claim_job(
        self, job_id: UUID, worker_id: str, now: datetime, lease_for: timedelta
    ) -> JobState | None: ...

    async def get_job(self, job_id: UUID) -> JobState: ...

    async def get_job_source(
        self, job_id: UUID, worker_id: str, attempt: int, now: datetime
    ) -> JobSource: ...

    async def heartbeat(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        *,
        stage: str,
        stage_rank: int,
        progress: int,
        now: datetime,
        lease_for: timedelta,
    ) -> bool: ...

    async def complete_success(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        artifact: ArtifactDetails,
        *,
        now: datetime,
    ) -> None: ...

    async def complete_failure(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        now: datetime,
        retry_at: datetime | None,
    ) -> JobState: ...


class ExecutionRunner(Protocol):
    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
    ) -> RunnerArtifactView: ...

    async def status(self, task_id: str) -> RunnerProgressView: ...

    async def cancel(self, task_id: str) -> None: ...


class ExecutionStorage(Protocol):
    async def upload(self, object_key: str, source: Path, content_type: str) -> int: ...

    async def delete(self, object_key: str) -> None: ...


class UrlDecryptor(Protocol):
    def decrypt(self, envelope: EncryptedUrl) -> str: ...


class WorkspaceCleaner(Protocol):
    async def cleanup(self, task_id: str, workspace: Path | None) -> None: ...


type Clock = Callable[[], datetime]
