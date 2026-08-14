from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from app.application.analysis_execution import (
    AnalysisDisposition,
    AnalysisExecution,
    VideoAnalysisRequest,
)

from .fakes import (
    NOW,
    FakeLoader,
    FakeRepository,
    running_job,
    settings,
)
from .fixtures import valid_mapping


class FakeAnalyzer:
    def __init__(self, output: object) -> None:
        self.output = output

    async def analyze(self, request: VideoAnalysisRequest) -> object:
        if isinstance(self.output, BaseException):
            raise self.output
        return self.output


class BlockingAnalyzer:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = False

    async def analyze(self, request: VideoAnalysisRequest) -> object:
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        raise AssertionError("unreachable")


class ProviderFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def execution(
    repository: FakeRepository,
    loader: FakeLoader,
    *,
    analyzer: object,
) -> AnalysisExecution:
    return AnalysisExecution(
        repository=repository,  # type: ignore[arg-type]
        loader=loader,
        analyzer=analyzer,  # type: ignore[arg-type]
        clock=lambda: NOW,
        settings=settings(),
    )


@pytest.mark.asyncio
async def test_success_runs_linear_stages_publishes_and_cleans(tmp_path: Path) -> None:
    repository = FakeRepository(running_job())
    loader = FakeLoader(tmp_path)

    disposition = await execution(
        repository, loader, analyzer=FakeAnalyzer(valid_mapping())
    ).execute(
        repository.job.id,
        repository.job.run_id,
        repository.job.run_no,
        repository.job.version,
    )

    assert disposition is AnalysisDisposition.ACK
    assert [stage for stage, _ in repository.heartbeats] == [
        "preparing",
        "analyzing",
        "validating",
    ]
    assert repository.job.status == "succeeded"
    assert len(repository.published) == 1
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_cancelled_lease_cancels_active_provider_and_cleans(
    tmp_path: Path,
) -> None:
    repository = FakeRepository(running_job())
    repository.heartbeat_failure_stage = "analyzing"
    loader = FakeLoader(tmp_path)
    analyzer = BlockingAnalyzer()

    disposition = await execution(repository, loader, analyzer=analyzer).execute(
        repository.job.id,
        repository.job.run_id,
        repository.job.run_no,
        repository.job.version,
    )

    assert analyzer.started.is_set()
    assert analyzer.cancelled is True
    assert repository.job.status == "cancelled"
    assert disposition is AnalysisDisposition.ACK
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_rate_limit_records_retry_and_cleans(tmp_path: Path) -> None:
    repository = FakeRepository(running_job())
    loader = FakeLoader(tmp_path)
    disposition = await execution(
        repository,
        loader,
        analyzer=FakeAnalyzer(ProviderFailure("analysis_provider_rate_limited")),
    ).execute(
        repository.job.id,
        repository.job.run_id,
        repository.job.run_no,
        repository.job.version,
    )

    assert disposition is AnalysisDisposition.ACK
    assert repository.job.status == "retry_wait"
    assert repository.failures[0]["error_code"] == "analysis_provider_rate_limited"
    assert repository.failures[0]["retryable"] is True
    assert repository.failures[0]["retry_at"] is not None
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_invalid_model_evidence_retries_with_attempt_limit(
    tmp_path: Path,
) -> None:
    repository = FakeRepository(running_job())
    loader = FakeLoader(tmp_path)
    invalid = valid_mapping()
    invalid["summary"] = {
        "text": "invented",
        "evidence_shot_ids": ["not-real"],
    }

    disposition = await execution(
        repository, loader, analyzer=FakeAnalyzer(invalid)
    ).execute(
        repository.job.id,
        repository.job.run_id,
        repository.job.run_no,
        repository.job.version,
    )

    assert disposition is AnalysisDisposition.ACK
    assert repository.job.status == "retry_wait"
    assert repository.failures[0]["error_code"] == "invalid_model_output"
    assert repository.failures[0]["retryable"] is True
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_screenplay_never_falls_back_to_video_executor(tmp_path: Path) -> None:
    job = replace(
        running_job(),
        artifact_id=None,
        document_id=uuid4(),
        input_kind="screenplay",
        result_contract="screenplay-analysis",
    )
    repository = FakeRepository(job)
    loader = FakeLoader(tmp_path)

    disposition = await execution(
        repository, loader, analyzer=FakeAnalyzer(valid_mapping())
    ).execute(job.id, job.run_id, job.run_no, job.version)

    assert disposition is AnalysisDisposition.ACK
    assert repository.job.status == "failed"
    assert repository.failures[0]["error_code"] == "analysis_cli_unsupported"
    assert repository.heartbeats == []
    assert loader.cleaned is False
