from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import AnalysisResult

from .models import (
    AnalysisArtifactSource,
    AnalysisScreenplaySource,
    LocalAnalysisArtifact,
    LocalScreenplayArtifact,
    VideoAnalysisRequest,
)


class AnalysisExecutionRepository(Protocol):
    async def claim_job(
        self,
        job_id: UUID,
        run_id: UUID,
        run_no: int,
        expected_version: int,
        worker_id: str,
        now: datetime,
        lease_for: timedelta,
    ) -> AnalysisJobSnapshot | None: ...

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None: ...

    async def get_artifact_source(
        self, job: AnalysisJobSnapshot, now: datetime
    ) -> AnalysisArtifactSource: ...

    async def get_screenplay_source(
        self, job: AnalysisJobSnapshot, now: datetime
    ) -> AnalysisScreenplaySource: ...

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
    ) -> bool: ...

    async def publish_result(
        self,
        job_id: UUID,
        run_id: UUID,
        worker_id: str,
        expected_version: int,
        result: AnalysisResult,
        provider: str,
        model: str,
        cli_version: str,
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
    ) -> AnalysisJobSnapshot: ...


class ArtifactLoader(Protocol):
    async def materialize(
        self,
        source: AnalysisArtifactSource,
        *,
        job_id: UUID,
        attempt: int,
    ) -> LocalAnalysisArtifact: ...

    async def cleanup(self, local: LocalAnalysisArtifact) -> None: ...


class ScreenplayArtifactLoader(Protocol):
    async def materialize(
        self,
        source: AnalysisScreenplaySource,
        *,
        job_id: UUID,
        attempt: int,
    ) -> LocalScreenplayArtifact: ...

    async def cleanup(self, local: LocalScreenplayArtifact) -> None: ...


class VideoAnalyzer(Protocol):
    async def analyze(self, request: VideoAnalysisRequest) -> object: ...


@dataclass(frozen=True, slots=True)
class AnalyzerSelection:
    analyzer: VideoAnalyzer
    provider: str
    model: str
    cli_version: str


class AnalyzerResolver(Protocol):
    async def resolve(self) -> AnalyzerSelection: ...


type Clock = Callable[[], datetime]
type AsyncOperation[ResultT] = Callable[[], Coroutine[Any, Any, ResultT]]
