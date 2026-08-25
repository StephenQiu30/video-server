from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisErrorCode,
    AnalysisInputKind,
    AnalysisStage,
    AnalysisStatus,
    AnalysisValidationError,
)

from .errors import (
    AnalysisLeaseLost,
    AnalysisOwnershipLost,
    AnalysisPersistenceRejected,
    AnalysisPersistenceUnavailable,
    AnalysisSourceUnavailable,
    classify_analysis_failure,
)
from .models import (
    AnalysisDisposition,
    AnalysisExecutionOutput,
    AnalysisExecutionSettings,
)
from .monitor import AnalysisLeaseMonitor
from .ports import (
    AnalysisExecutionRepository,
    AnalyzerResolver,
    ArtifactLoader,
    Clock,
    VideoAnalyzer,
)
from .transitions import AnalysisTransitions
from .video_executor import StaticAnalyzerResolver, VideoAnalysisExecutor


class ClaimedAnalysisExecutor(Protocol):
    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput: ...


class AnalysisExecution:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        loader: ArtifactLoader,
        analyzer: VideoAnalyzer | None = None,
        resolver: AnalyzerResolver | None = None,
        screenplay_executor: ClaimedAnalysisExecutor | None = None,
        clock: Clock,
        settings: AnalysisExecutionSettings,
    ) -> None:
        self._repository = repository
        if resolver is None:
            if analyzer is None:
                raise ValueError("an analyzer or resolver is required")
            resolver = StaticAnalyzerResolver(
                analyzer,
                provider=settings.provider,
                model=settings.model,
                cli_version=settings.cli_version,
            )
        self._clock = clock
        self._settings = settings
        self._transitions = AnalysisTransitions(repository, settings, clock)
        self._executors: dict[AnalysisInputKind, ClaimedAnalysisExecutor] = {
            AnalysisInputKind.VIDEO: VideoAnalysisExecutor(
                repository=repository,
                loader=loader,
                resolver=resolver,
                clock=clock,
            )
        }
        if screenplay_executor is not None:
            self._executors[AnalysisInputKind.SCREENPLAY] = screenplay_executor

    async def execute(
        self, job_id: UUID, run_id: UUID, run_no: int, expected_version: int
    ) -> AnalysisDisposition:
        try:
            claimed = await self._repository.claim_job(
                job_id,
                run_id,
                run_no,
                expected_version,
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
        executor = self._executor(job.input_kind)
        if executor is None:
            return await self._transitions.fail(
                job.id, job.attempt, AnalysisErrorCode.CLI_UNSUPPORTED
            )
        try:
            output = await executor.execute(job, monitor)
            await monitor.advance(AnalysisStage.VALIDATING, 90)
            current = await self._repository.get_job(job.id)
            if current is None or not _owns(
                current, self._settings.worker_id, job.attempt, self._clock()
            ):
                raise AnalysisLeaseLost
            await self._repository.publish_result(
                job.id,
                current.run_id,
                self._settings.worker_id,
                current.version,
                output.result,
                output.provider,
                output.model,
                output.cli_version,
                self._clock(),
            )
            return AnalysisDisposition.ACK
        except (AnalysisLeaseLost, AnalysisOwnershipLost):
            return await self._transitions.converge(job.id)
        except AnalysisPersistenceUnavailable:
            return AnalysisDisposition.REQUEUE
        except AnalysisPersistenceRejected:
            return await self._transitions.fail(
                job.id, job.attempt, AnalysisErrorCode.INTERNAL_ERROR
            )
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
                classify_analysis_failure(error, AnalysisStage.ANALYZING),
            )

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

    def _executor(self, input_kind: str) -> ClaimedAnalysisExecutor | None:
        try:
            return self._executors.get(AnalysisInputKind(input_kind))
        except ValueError:
            return None


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
