from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.downloads.enums import (
    DownloadErrorCode,
    DownloadStage,
    DownloadStatus,
)
from app.domain.downloads.errors import InvalidJobTransition
from app.domain.downloads.formats import DownloadPlan
from app.domain.downloads.job_rules import (
    DownloadJobRules,
    require_linear_stage,
    valid_duration,
    valid_owner,
    valid_time,
)


@dataclass(slots=True)
class DownloadJob(DownloadJobRules):
    id: str
    plan: DownloadPlan
    status: DownloadStatus = DownloadStatus.QUEUED
    stage: DownloadStage | None = None
    progress: int = 0
    attempt: int = 0
    version: int = 0
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    retry_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: DownloadErrorCode | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("job id cannot be blank")
        self.id = self.id.strip()
        if not 0 <= self.progress <= 100:
            raise ValueError("progress must be between 0 and 100")
        if self.attempt < 0 or self.version < 0:
            raise ValueError("attempt and version cannot be negative")

    @classmethod
    def create(cls, job_id: str, plan: DownloadPlan) -> DownloadJob:
        return cls(id=job_id, plan=plan)

    def claim(self, owner: str, now: datetime, lease_duration: timedelta) -> None:
        self._require_status(DownloadStatus.QUEUED)
        owner = valid_owner(owner)
        valid_time(now)
        valid_duration(lease_duration)
        self.status = DownloadStatus.RUNNING
        self.stage = DownloadStage.REVALIDATING
        self.attempt += 1
        self.lease_owner = owner
        self.lease_expires_at = now + lease_duration
        self.heartbeat_at = now
        self.started_at = self.started_at or now
        self.retry_at = None
        self.finished_at = None
        self.error_code = None
        self._bump()

    def heartbeat(self, owner: str, now: datetime, lease_duration: timedelta) -> None:
        self._require_active_lease(owner, now)
        valid_duration(lease_duration)
        self.heartbeat_at = now
        self.lease_expires_at = now + lease_duration
        self._bump()

    def advance(
        self,
        owner: str,
        stage: DownloadStage,
        progress: int,
        now: datetime,
    ) -> None:
        self._require_active_lease(owner, now)
        if self.stage is None:
            raise InvalidJobTransition("running job has no stage")
        require_linear_stage(self.stage, stage)
        if isinstance(progress, bool) or not 0 <= progress <= 100:
            raise InvalidJobTransition("progress must be between 0 and 100")
        if progress < self.progress:
            raise InvalidJobTransition("progress cannot decrease")
        self.stage = stage
        self.progress = progress
        self._bump()

    def succeed(self, owner: str, now: datetime) -> None:
        self._require_active_lease(owner, now)
        if self.stage is not DownloadStage.UPLOADING:
            raise InvalidJobTransition("job must finish uploading before success")
        self.status = DownloadStatus.SUCCEEDED
        self.stage = None
        self.progress = 100
        self.error_code = None
        self.finished_at = now
        self._clear_lease()
        self._bump()

    def schedule_retry(
        self,
        owner: str,
        error_code: DownloadErrorCode,
        now: datetime,
        retry_at: datetime,
    ) -> None:
        self._require_active_lease(owner, now)
        valid_time(retry_at)
        if not error_code.retryable:
            raise InvalidJobTransition("non-retryable error cannot be scheduled")
        if retry_at <= now:
            raise InvalidJobTransition("retry time must be in the future")
        self.status = DownloadStatus.RETRY_WAIT
        self.stage = None
        self.error_code = error_code
        self.retry_at = retry_at
        self._clear_lease()
        self._bump()

    def release_retry(self, now: datetime) -> None:
        self._require_status(DownloadStatus.RETRY_WAIT)
        valid_time(now)
        if self.retry_at is None or now < self.retry_at:
            raise InvalidJobTransition("retry is not ready")
        self.status = DownloadStatus.QUEUED
        self.retry_at = None
        self._bump()

    def recover_expired_lease(
        self, now: datetime, retry_at: datetime, max_attempts: int
    ) -> None:
        self._require_status(DownloadStatus.RUNNING)
        valid_time(now)
        valid_time(retry_at)
        if self.lease_expires_at is None or now < self.lease_expires_at:
            raise InvalidJobTransition("lease has not expired")
        if max_attempts <= 0:
            raise ValueError("max attempts must be positive")
        self.error_code = DownloadErrorCode.WORKER_LOST
        self.stage = None
        self._clear_lease()
        if self.attempt >= max_attempts:
            self.status = DownloadStatus.FAILED
            self.retry_at = None
            self.finished_at = now
        else:
            if retry_at < now:
                raise InvalidJobTransition("retry time cannot be in the past")
            self.status = DownloadStatus.RETRY_WAIT
            self.retry_at = retry_at
        self._bump()

    def fail(
        self,
        error_code: DownloadErrorCode,
        now: datetime,
        owner: str | None = None,
    ) -> None:
        if error_code is DownloadErrorCode.CANCELLED:
            raise InvalidJobTransition("use cancel for cancellation")
        if self.status is DownloadStatus.RUNNING:
            if owner is None:
                raise InvalidJobTransition("running failure requires lease owner")
            self._require_active_lease(owner, now)
        elif self.status not in {DownloadStatus.QUEUED, DownloadStatus.RETRY_WAIT}:
            raise InvalidJobTransition("job cannot fail from current status")
        valid_time(now)
        self.status = DownloadStatus.FAILED
        self.stage = None
        self.error_code = error_code
        self.retry_at = None
        self.finished_at = now
        self._clear_lease()
        self._bump()

    def cancel(self, now: datetime) -> None:
        if self.status not in {
            DownloadStatus.QUEUED,
            DownloadStatus.RUNNING,
            DownloadStatus.RETRY_WAIT,
        }:
            raise InvalidJobTransition("job cannot be cancelled from current status")
        valid_time(now)
        self.status = DownloadStatus.CANCELLED
        self.stage = None
        self.error_code = DownloadErrorCode.CANCELLED
        self.retry_at = None
        self.finished_at = now
        self._clear_lease()
        self._bump()
