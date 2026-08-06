from __future__ import annotations

from datetime import datetime

from app.domain.analysis.enums import AnalysisErrorCode, AnalysisStatus
from app.domain.analysis.errors import InvalidAnalysisTransition
from app.domain.analysis.job import AnalysisJob
from app.domain.analysis.job_rules import valid_time


def schedule_retry(
    job: AnalysisJob,
    owner: str,
    error_code: AnalysisErrorCode,
    now: datetime,
    retry_at: datetime,
) -> None:
    job._require_active_lease(owner, now)
    valid_time(retry_at)
    if not error_code.retryable:
        raise InvalidAnalysisTransition("non-retryable error cannot be scheduled")
    if retry_at <= now:
        raise InvalidAnalysisTransition("retry time must be in the future")
    job.status = AnalysisStatus.RETRY_WAIT
    job.stage = None
    job.error_code = error_code
    job.retry_at = retry_at
    job._clear_lease()
    job._bump()


def release_retry(job: AnalysisJob, now: datetime) -> None:
    job._require_status(AnalysisStatus.RETRY_WAIT)
    valid_time(now)
    if job.retry_at is None or now < job.retry_at:
        raise InvalidAnalysisTransition("retry is not ready")
    job.status = AnalysisStatus.QUEUED
    job.retry_at = None
    job._bump()


def recover_expired_lease(
    job: AnalysisJob, now: datetime, retry_at: datetime, max_attempts: int
) -> None:
    job._require_status(AnalysisStatus.RUNNING)
    valid_time(now)
    valid_time(retry_at)
    if job.lease_expires_at is None or now < job.lease_expires_at:
        raise InvalidAnalysisTransition("lease has not expired")
    if max_attempts <= 0:
        raise ValueError("max attempts must be positive")
    job.error_code = AnalysisErrorCode.WORKER_LOST
    job.stage = None
    job._clear_lease()
    if job.attempt >= max_attempts:
        job.status = AnalysisStatus.FAILED
        job.retry_at = None
        job.finished_at = now
    else:
        if retry_at < now:
            raise InvalidAnalysisTransition("retry time cannot be in the past")
        job.status = AnalysisStatus.RETRY_WAIT
        job.retry_at = retry_at
    job._bump()


def fail(
    job: AnalysisJob,
    error_code: AnalysisErrorCode,
    now: datetime,
    owner: str | None,
) -> None:
    if error_code is AnalysisErrorCode.CANCELLED:
        raise InvalidAnalysisTransition("use cancel for cancellation")
    if job.status is AnalysisStatus.RUNNING:
        if owner is None:
            raise InvalidAnalysisTransition("running failure requires lease owner")
        job._require_active_lease(owner, now)
    elif job.status not in {AnalysisStatus.QUEUED, AnalysisStatus.RETRY_WAIT}:
        raise InvalidAnalysisTransition("analysis cannot fail from current status")
    valid_time(now)
    job.status = AnalysisStatus.FAILED
    job.stage = None
    job.error_code = error_code
    job.retry_at = None
    job.finished_at = now
    job._clear_lease()
    job._bump()


def cancel(job: AnalysisJob, now: datetime) -> None:
    if job.status not in {
        AnalysisStatus.QUEUED,
        AnalysisStatus.RUNNING,
        AnalysisStatus.RETRY_WAIT,
    }:
        raise InvalidAnalysisTransition("analysis cannot be cancelled")
    valid_time(now)
    job.status = AnalysisStatus.CANCELLED
    job.stage = None
    job.error_code = AnalysisErrorCode.CANCELLED
    job.retry_at = None
    job.finished_at = now
    job._clear_lease()
    job._bump()
