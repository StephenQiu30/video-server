from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.analysis.enums import (
    AnalysisErrorCode,
    AnalysisStage,
    AnalysisStatus,
)
from app.domain.analysis.errors import InvalidAnalysisTransition
from app.domain.analysis.job_rules import (
    AnalysisJobRules,
    require_linear_stage,
    valid_duration,
    valid_owner,
    valid_time,
)
from app.domain.analysis.text import identifier, required_text


@dataclass(slots=True)
class AnalysisJob(AnalysisJobRules):
    id: str
    artifact_id: str
    input_sha256: str
    skill_id: str
    output_language: str
    status: AnalysisStatus = AnalysisStatus.QUEUED
    stage: AnalysisStage | None = None
    progress: int = 0
    attempt: int = 0
    version: int = 0
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    retry_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: AnalysisErrorCode | None = None

    def __post_init__(self) -> None:
        self.id = identifier(self.id, "analysis job id")
        self.artifact_id = identifier(self.artifact_id, "artifact id")
        if len(self.input_sha256) != 64 or any(
            value not in "0123456789abcdef" for value in self.input_sha256
        ):
            raise ValueError("input_sha256 must be lowercase SHA-256")
        self.skill_id = required_text(self.skill_id, "analysis skill id", maximum=128)
        self.output_language = required_text(
            self.output_language, "output language", maximum=35
        )
        if isinstance(self.progress, bool) or not 0 <= self.progress <= 100:
            raise ValueError("progress must be between 0 and 100")
        if self.attempt < 0 or self.version < 0:
            raise ValueError("attempt and version cannot be negative")

    @classmethod
    def create(
        cls,
        *,
        job_id: str,
        artifact_id: str,
        input_sha256: str,
        skill_id: str,
        output_language: str,
    ) -> AnalysisJob:
        return cls(
            id=job_id,
            artifact_id=artifact_id,
            input_sha256=input_sha256,
            skill_id=skill_id,
            output_language=output_language,
        )

    def claim(self, owner: str, now: datetime, lease_duration: timedelta) -> None:
        self._require_status(AnalysisStatus.QUEUED)
        owner = valid_owner(owner)
        valid_time(now)
        valid_duration(lease_duration)
        self.status = AnalysisStatus.RUNNING
        self.stage = AnalysisStage.PREPARING
        self.progress = 0
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
        self, owner: str, stage: AnalysisStage, progress: int, now: datetime
    ) -> None:
        self._require_active_lease(owner, now)
        if self.stage is None:
            raise InvalidAnalysisTransition("running analysis has no stage")
        require_linear_stage(self.stage, stage)
        if isinstance(progress, bool) or not 0 <= progress <= 100:
            raise InvalidAnalysisTransition("progress must be between 0 and 100")
        if progress < self.progress:
            raise InvalidAnalysisTransition("progress cannot decrease")
        self.stage = stage
        self.progress = progress
        self._bump()

    def succeed(self, owner: str, now: datetime) -> None:
        self._require_active_lease(owner, now)
        if self.stage is not AnalysisStage.VALIDATING:
            raise InvalidAnalysisTransition("analysis must validate before success")
        self.status = AnalysisStatus.SUCCEEDED
        self.stage = None
        self.progress = 100
        self.error_code = None
        self.finished_at = now
        self._clear_lease()
        self._bump()

    def schedule_retry(
        self,
        owner: str,
        error_code: AnalysisErrorCode,
        now: datetime,
        retry_at: datetime,
    ) -> None:
        from app.domain.analysis.job_failures import schedule_retry

        schedule_retry(self, owner, error_code, now, retry_at)

    def release_retry(self, now: datetime) -> None:
        from app.domain.analysis.job_failures import release_retry

        release_retry(self, now)

    def recover_expired_lease(
        self, now: datetime, retry_at: datetime, max_attempts: int
    ) -> None:
        from app.domain.analysis.job_failures import recover_expired_lease

        recover_expired_lease(self, now, retry_at, max_attempts)

    def fail(
        self,
        error_code: AnalysisErrorCode,
        now: datetime,
        owner: str | None = None,
    ) -> None:
        from app.domain.analysis.job_failures import fail

        fail(self, error_code, now, owner)

    def cancel(self, now: datetime) -> None:
        from app.domain.analysis.job_failures import cancel

        cancel(self, now)
