from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from uuid import UUID

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisErrorCode,
    AnalysisMedia,
    AnalysisStage,
    AnalysisStatus,
    AnalysisValidationError,
    parse_analysis_result,
)

from .errors import (
    AnalysisLeaseLost,
    AnalysisOwnershipLost,
    AnalysisPersistenceUnavailable,
    AnalysisSourceUnavailable,
    classify_analysis_failure,
)
from .models import (
    AnalysisDisposition,
    AnalysisExecutionSettings,
    LocalAnalysisArtifact,
    VideoAnalysisRequest,
)
from .monitor import AnalysisLeaseMonitor
from .ports import (
    AnalysisExecutionRepository,
    ArtifactLoader,
    Clock,
    VideoAnalyzer,
)
from .transitions import AnalysisTransitions


class AnalysisExecution:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        loader: ArtifactLoader,
        analyzer: VideoAnalyzer,
        clock: Clock,
        settings: AnalysisExecutionSettings,
    ) -> None:
        self._repository = repository
        self._loader = loader
        self._analyzer = analyzer
        self._clock = clock
        self._settings = settings
        self._transitions = AnalysisTransitions(repository, settings, clock)

    async def execute(self, job_id: UUID) -> AnalysisDisposition:
        try:
            claimed = await self._repository.claim_job(
                job_id,
                self._settings.worker_id,
                self._clock(),
                self._settings.lease_for,
            )
        except AnalysisSourceUnavailable:
            return AnalysisDisposition.ACK
        except Exception:
            return AnalysisDisposition.REQUEUE
        if claimed is None:
            return await self._transitions.converge(job_id)
        return await self._execute_claimed(claimed)

    async def _execute_claimed(self, job: AnalysisJobSnapshot) -> AnalysisDisposition:
        monitor = self._monitor(job.id, job.attempt)
        local: LocalAnalysisArtifact | None = None
        stage = AnalysisStage.PREPARING
        try:
            source = await self._repository.get_artifact_source(job, self._clock())
            local = await monitor.run(
                lambda: self._loader.materialize(
                    source, job_id=job.id, attempt=job.attempt
                ),
                stage=stage,
                progress=10,
            )
            stage = AnalysisStage.ANALYZING
            request = VideoAnalysisRequest(
                artifact=local.artifact,
                workspace=local.workspace,
                duration_ms=source.duration_ms,
                size_bytes=source.size_bytes,
                container=source.container,
                output_language=job.output_language,
                schema_version=job.schema_version,
                prompt_version=self._settings.prompt_version,
            )
            payload = await monitor.run(
                lambda: self._analyzer.analyze(request),
                stage=stage,
                progress=70,
            )
            result = parse_analysis_result(
                payload,
                AnalysisMedia(
                    duration_ms=source.duration_ms,
                    container=source.container,
                    size_bytes=source.size_bytes,
                ),
                expected_schema_version=job.schema_version,
                expected_language=job.output_language,
            )
            stage = AnalysisStage.VALIDATING
            await monitor.advance(stage, 90)
            current = await self._repository.get_job(job.id)
            if current is None or not _owns(
                current, self._settings.worker_id, job.attempt, self._clock()
            ):
                raise AnalysisLeaseLost
            await self._repository.publish_result(
                job.id,
                self._settings.worker_id,
                current.version,
                result,
                self._settings.provider,
                self._settings.model,
                self._settings.cli_version,
                self._settings.prompt_version,
                self._clock(),
            )
            return AnalysisDisposition.ACK
        except (AnalysisLeaseLost, AnalysisOwnershipLost):
            return await self._transitions.converge(job.id)
        except AnalysisPersistenceUnavailable:
            return AnalysisDisposition.REQUEUE
        except AnalysisSourceUnavailable:
            return await self._transitions.fail(
                job.id, job.attempt, AnalysisErrorCode.INPUT_ARTIFACT_UNAVAILABLE
            )
        except asyncio.CancelledError:
            raise
        except AnalysisValidationError:
            return await self._transitions.fail(
                job.id, job.attempt, AnalysisErrorCode.INVALID_MODEL_OUTPUT
            )
        except Exception as error:
            return await self._transitions.fail(
                job.id,
                job.attempt,
                classify_analysis_failure(error, stage),
            )
        finally:
            if local is not None:
                with suppress(Exception):
                    await self._loader.cleanup(local)

    def _monitor(self, job_id: UUID, attempt: int) -> AnalysisLeaseMonitor:
        return AnalysisLeaseMonitor(
            repository=self._repository,
            job_id=job_id,
            worker_id=self._settings.worker_id,
            attempt=attempt,
            clock=self._clock,
            lease_for=self._settings.lease_for,
            interval=self._settings.heartbeat_interval,
        )


def _owns(
    job: AnalysisJobSnapshot, worker_id: str, attempt: int, now: datetime
) -> bool:
    return (
        job.status == AnalysisStatus.RUNNING.value
        and job.stage == AnalysisStage.VALIDATING.value
        and job.lease_owner == worker_id
        and job.attempt == attempt
        and job.lease_expires_at is not None
        and now < job.lease_expires_at
    )
