from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.application.analysis import AnalysisJobSnapshot, AudioChunk
from app.application.analysis_execution import (
    AnalysisArtifactSource,
    AnalysisExecutionSettings,
    LocalAnalysisArtifact,
)
from app.domain.analysis import AnalysisResult, Transcript, TranscriptSegment

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def running_job() -> AnalysisJobSnapshot:
    return AnalysisJobSnapshot(
        id=uuid4(),
        artifact_id=uuid4(),
        owner_hash="a" * 64,
        request_fingerprint="b" * 64,
        input_sha256="c" * 64,
        profile="default",
        schema_version="analysis.v1",
        output_language="zh-CN",
        status="running",
        stage="preparing",
        progress=0,
        attempt=1,
        max_attempts=3,
        version=1,
        lease_owner="analysis-worker",
        lease_expires_at=NOW + timedelta(minutes=5),
        heartbeat_at=NOW,
        started_at=NOW,
        retry_at=None,
        finished_at=None,
        error_code=None,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeRepository:
    def __init__(self, job: AnalysisJobSnapshot) -> None:
        self.job = job
        self.heartbeats: list[tuple[str, int]] = []
        self.failures: list[dict[str, object]] = []
        self.published: list[AnalysisResult] = []
        self.source_error: Exception | None = None
        self.heartbeat_failure_stage: str | None = None
        self._stage_counts: dict[str, int] = {}

    async def claim_job(
        self, job_id: UUID, worker_id: str, now: datetime, lease_for: timedelta
    ) -> AnalysisJobSnapshot | None:
        return self.job if job_id == self.job.id else None

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None:
        return self.job if job_id == self.job.id else None

    async def get_artifact_source(
        self, job: AnalysisJobSnapshot, now: datetime
    ) -> AnalysisArtifactSource:
        if self.source_error is not None:
            raise self.source_error
        return AnalysisArtifactSource(
            job.artifact_id,
            "video-artifacts",
            f"downloads/{job.id}/1/video.mp4",
            job.input_sha256,
            5,
            "mp4",
        )

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
        self.heartbeats.append((stage, progress))
        count = self._stage_counts.get(stage, 0) + 1
        self._stage_counts[stage] = count
        if self.heartbeat_failure_stage == stage and count > 1:
            self.job = replace(
                self.job,
                status="cancelled",
                stage=None,
                lease_owner=None,
                lease_expires_at=None,
            )
            return False
        self.job = replace(
            self.job,
            stage=stage,
            progress=progress,
            version=self.job.version + 1,
            lease_expires_at=now + lease_for,
        )
        return True

    async def publish_result(
        self,
        job_id: UUID,
        worker_id: str,
        expected_version: int,
        result: AnalysisResult,
        now: datetime,
    ) -> None:
        assert expected_version == self.job.version
        self.published.append(result)
        self.job = replace(self.job, status="succeeded", stage=None)

    async def complete_failure(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        **values: object,
    ) -> AnalysisJobSnapshot:
        self.failures.append(values)
        status = "retry_wait" if values["retryable"] else "failed"
        self.job = replace(self.job, status=status, stage=None)
        return self.job


class FakeLoader:
    def __init__(self, root: Path) -> None:
        self.local = LocalAnalysisArtifact(root, root / "source.mp4")
        self.cleaned = False

    async def materialize(
        self, source: AnalysisArtifactSource, *, job_id: UUID, attempt: int
    ) -> LocalAnalysisArtifact:
        return self.local

    async def cleanup(self, local: LocalAnalysisArtifact) -> None:
        self.cleaned = True


class FakePreprocessor:
    async def extract_chunks(
        self, artifact: Path, *, workspace: Path
    ) -> tuple[AudioChunk, ...]:
        return (AudioChunk(0, 0, 2_000, b"wav"),)


class FakeTranscriber:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def transcribe(
        self, chunks: tuple[AudioChunk, ...], language_hint: str | None
    ) -> Transcript:
        if self.failure is not None:
            raise self.failure
        return transcript()


def transcript() -> Transcript:
    return Transcript((TranscriptSegment("seg-a", 0, 2_000, "en", "Evidence"),))


def settings() -> AnalysisExecutionSettings:
    return AnalysisExecutionSettings(
        worker_id="analysis-worker",
        bucket="video-artifacts",
        lease_for=timedelta(seconds=30),
        heartbeat_interval=0.01,
        max_source_bytes=1024,
    )
