from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import UUID

from app.application.analysis import (
    AnalysisJobSnapshot,
    AnalysisPublish,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.application.analysis_execution import AnalysisArtifactSource
from app.application.analysis_execution.errors import (
    AnalysisOwnershipLost,
    AnalysisPersistenceUnavailable,
    AnalysisSourceUnavailable,
)
from app.domain.analysis import AnalysisResult
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database import (
    LeaseConflict,
    RepositoryConflict,
    RepositoryNotFound,
    SqlAlchemyDownloadRepository,
)


class AnalysisExecutionPersistence:
    def __init__(
        self,
        analysis: SqlAlchemyAnalysisRepository,
        downloads: SqlAlchemyDownloadRepository,
    ) -> None:
        self._analysis = analysis
        self._downloads = downloads

    async def claim_job(
        self, job_id: UUID, worker_id: str, now: datetime, lease_for: timedelta
    ) -> AnalysisJobSnapshot | None:
        with _translate_errors():
            return await self._analysis.claim_job(job_id, worker_id, now, lease_for)
        raise AssertionError("unreachable")

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None:
        with _translate_errors():
            return await self._analysis.get_job(job_id)
        raise AssertionError("unreachable")

    async def get_artifact_source(
        self, job: AnalysisJobSnapshot, now: datetime
    ) -> AnalysisArtifactSource:
        with _translate_errors():
            projection = await self._analysis.get_artifact(job.artifact_id)
            if (
                projection is None
                or projection.owner_hash != job.owner_hash
                or projection.download_status != "succeeded"
                or projection.sha256 != job.input_sha256
                or projection.expires_at <= now
            ):
                raise AnalysisSourceUnavailable
            artifact = await self._downloads.get_artifact(
                projection.download_id, projection.owner_hash, now
            )
            if artifact.id != projection.id or artifact.sha256 != job.input_sha256:
                raise AnalysisSourceUnavailable
            return AnalysisArtifactSource(
                artifact_id=artifact.id,
                bucket=artifact.bucket,
                object_key=artifact.object_key,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
                duration_ms=artifact.duration_ms,
                container=artifact.container,
            )
        raise AssertionError("unreachable")

    async def heartbeat(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        *,
        stage: str,
        progress: int,
        now: datetime,
        lease_for: timedelta,
    ) -> bool:
        with _translate_errors():
            return await self._analysis.heartbeat(
                job_id,
                worker_id,
                attempt,
                stage=stage,
                progress=progress,
                now=now,
                lease_for=lease_for,
            )
        raise AssertionError("unreachable")

    async def publish_result(
        self,
        job_id: UUID,
        worker_id: str,
        expected_version: int,
        result: AnalysisResult,
        provider: str,
        model: str,
        cli_version: str,
        prompt_version: str,
        now: datetime,
    ) -> None:
        with _translate_errors():
            await self._analysis.publish_result(
                AnalysisPublish(
                    job_id=job_id,
                    result=result,
                    lease_owner=worker_id,
                    expected_version=expected_version,
                    provider=provider,
                    model=model,
                    cli_version=cli_version,
                    prompt_version=prompt_version,
                    now=now,
                )
            )

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
    ) -> AnalysisJobSnapshot:
        with _translate_errors():
            return await self._analysis.complete_failure(
                job_id,
                worker_id,
                attempt,
                error_code=error_code,
                error_message=error_message,
                retryable=retryable,
                now=now,
                retry_at=retry_at,
            )
        raise AssertionError("unreachable")


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except (
        AnalysisOwnershipLost,
        AnalysisPersistenceUnavailable,
        AnalysisSourceUnavailable,
    ):
        raise
    except (PersistenceNotFound, RepositoryNotFound) as exc:
        raise AnalysisSourceUnavailable from exc
    except (PersistenceConflict, LeaseConflict, RepositoryConflict) as exc:
        raise AnalysisOwnershipLost from exc
    except Exception as exc:
        raise AnalysisPersistenceUnavailable from exc
