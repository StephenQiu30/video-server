from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from app.application.analysis import AnalysisJobSnapshot, AudioChunk
from app.domain.analysis import AnalysisResult, Transcript

from .models import AnalysisArtifactSource, LocalAnalysisArtifact


class AnalysisExecutionRepository(Protocol):
    async def claim_job(
        self, job_id: UUID, worker_id: str, now: datetime, lease_for: timedelta
    ) -> AnalysisJobSnapshot | None: ...

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None: ...

    async def get_artifact_source(
        self, job: AnalysisJobSnapshot, now: datetime
    ) -> AnalysisArtifactSource: ...

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
        worker_id: str,
        expected_version: int,
        result: AnalysisResult,
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


class AudioPreprocessor(Protocol):
    async def extract_chunks(
        self, artifact: Path, *, workspace: Path
    ) -> tuple[AudioChunk, ...]: ...


class Transcriber(Protocol):
    async def transcribe(
        self, chunks: tuple[AudioChunk, ...], language_hint: str | None
    ) -> Transcript: ...


class Analyzer(Protocol):
    async def analyze(self, transcript: Transcript, output_language: str) -> object: ...


type Clock = Callable[[], datetime]
type AsyncOperation[ResultT] = Callable[[], Coroutine[Any, Any, ResultT]]
