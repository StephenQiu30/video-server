from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.application.downloads import (
    ArtifactSnapshot,
    DownloadCreate,
    EncryptedUrl,
    FormatSnapshot,
    InspectionCreate,
    InspectionSaveResult,
    InspectionSnapshot,
    JobSaveResult,
    JobSnapshot,
    PersistenceIdempotencyConflict,
    RetrySourceSnapshot,
    RunnerInspection,
)


class FakeValidator:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def validate(self, url: str) -> str:
        self.seen.append(url)
        if not url.startswith(("https://", "http://")):
            raise ValueError("unsafe")
        return url


class FakeCipher:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def encrypt(self, url: str) -> EncryptedUrl:
        self.seen.append(url)
        return EncryptedUrl(b"opaque-ciphertext", b"nonce", "primary")

    def decrypt(self, envelope: EncryptedUrl) -> str:
        if envelope.key_id != "primary":
            raise ValueError("unknown key")
        return "https://example.com/video"


class FakeRunner:
    def __init__(self, inspection: RunnerInspection) -> None:
        self.inspection = inspection
        self.seen: list[str] = []

    async def inspect(self, url: str) -> RunnerInspection:
        self.seen.append(url)
        return self.inspection


class FakeStorage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str | None]] = []

    async def presigned_download(
        self, object_key: str, *, title: str | None = None, ttl_seconds: int
    ) -> str:
        self.calls.append((object_key, ttl_seconds, title))
        return "https://objects.example/download-token"


class FakeRepository:
    def __init__(self) -> None:
        self.inspections: dict[UUID, InspectionSnapshot] = {}
        self.jobs: dict[UUID, JobSnapshot] = {}
        self.artifacts: dict[UUID, ArtifactSnapshot] = {}
        self.inspection_commands: list[InspectionCreate] = []
        self.download_commands: list[DownloadCreate] = []
        self._inspection_keys: dict[tuple[str, str], UUID] = {}
        self._download_keys: dict[tuple[str, str], UUID] = {}
        self._download_fingerprints: dict[UUID, str] = {}
        self.outbox_events = 0
        self.retry_sources: dict[UUID, EncryptedUrl] = {}

    async def save_inspection(self, command: InspectionCreate) -> InspectionSaveResult:
        self.inspection_commands.append(command)
        key = (command.owner_hash, command.idempotency_key)
        existing_id = self._inspection_keys.get(key)
        if existing_id is not None:
            existing = self.inspections[existing_id]
            if existing.request_fingerprint != command.request_fingerprint:
                raise PersistenceIdempotencyConflict
            return InspectionSaveResult(existing, created=False)
        formats = tuple(
            FormatSnapshot(
                id=item.id,
                display_name=item.display_name,
                plan_fingerprint=item.plan_fingerprint,
                semantic_plan=item.semantic_plan,
                provider_hints=item.provider_hints,
                expires_at=item.expires_at,
            )
            for item in command.formats
        )
        snapshot = InspectionSnapshot(
            id=command.id,
            owner_hash=command.owner_hash,
            request_fingerprint=command.request_fingerprint,
            extractor_key=command.extractor_key,
            provider_media_id=command.provider_media_id,
            title=command.title,
            duration_seconds=command.duration_seconds,
            metadata=command.metadata,
            expires_at=command.expires_at,
            formats=formats,
        )
        self.inspections[command.id] = snapshot
        self._inspection_keys[key] = command.id
        return InspectionSaveResult(snapshot, created=True)

    async def get_inspection(
        self, inspection_id: UUID, owner_hash: str, now: datetime
    ) -> InspectionSnapshot | None:
        del owner_hash, now
        return self.inspections.get(inspection_id)

    async def create_job(
        self, command: DownloadCreate, *, now: datetime
    ) -> JobSaveResult:
        self.download_commands.append(command)
        key = (command.owner_hash, command.idempotency_key)
        existing_id = self._download_keys.get(key)
        if existing_id is not None:
            existing = self.jobs[existing_id]
            if self._download_fingerprints[existing_id] != command.request_fingerprint:
                raise PersistenceIdempotencyConflict
            return JobSaveResult(existing, created=False)
        job = JobSnapshot.queued(command, now=now)
        self.jobs[job.id] = job
        self._download_keys[key] = job.id
        self._download_fingerprints[job.id] = command.request_fingerprint
        self.outbox_events += 1
        return JobSaveResult(job, created=True)

    async def get_job(self, job_id: UUID) -> JobSnapshot | None:
        return self.jobs.get(job_id)

    async def get_retry_source(
        self, job_id: UUID, owner_hash: str
    ) -> RetrySourceSnapshot | None:
        job = self.jobs.get(job_id)
        if job is None or job.owner_hash != owner_hash:
            return None
        source = self.retry_sources.get(
            job_id, EncryptedUrl(b"opaque-ciphertext", b"nonce", "primary")
        )
        return RetrySourceSnapshot(encrypted_url=source)

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> JobSnapshot | None:
        job = self.jobs.get(job_id)
        if job is None or job.owner_hash != owner_hash:
            return None
        cancelled = replace(
            job,
            status="cancelled",
            stage=None,
            error_code="cancelled",
            finished_at=now,
            updated_at=now,
        )
        self.jobs[job_id] = cancelled
        return cancelled

    async def get_artifact(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> ArtifactSnapshot | None:
        job = self.jobs.get(job_id)
        artifact = self.artifacts.get(job_id)
        if (
            job is None
            or job.owner_hash != owner_hash
            or artifact is None
            or artifact.expires_at <= now
        ):
            return None
        return artifact
