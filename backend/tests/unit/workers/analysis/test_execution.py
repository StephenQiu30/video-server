from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app.application.analysis_execution import AnalysisDisposition, AnalysisExecution
from app.domain.analysis import Transcript

from .fakes import (
    NOW,
    FakeLoader,
    FakePreprocessor,
    FakeRepository,
    FakeTranscriber,
    running_job,
    settings,
)
from .fixtures import valid_mapping


class FakeAnalyzer:
    def __init__(self, output: object) -> None:
        self.output = output

    async def analyze(self, transcript: Transcript, output_language: str) -> object:
        return self.output


class BlockingAnalyzer:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = False

    async def analyze(self, transcript: Transcript, output_language: str) -> object:
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
    transcriber: FakeTranscriber | None = None,
) -> AnalysisExecution:
    return AnalysisExecution(
        repository=repository,  # type: ignore[arg-type]
        loader=loader,
        preprocessor=FakePreprocessor(),
        transcriber=transcriber or FakeTranscriber(),
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
    ).execute(repository.job.id)

    assert disposition is AnalysisDisposition.ACK
    assert [stage for stage, _ in repository.heartbeats] == [
        "preparing",
        "transcribing",
        "transcribing",
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
        repository.job.id
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
    transcriber = FakeTranscriber(ProviderFailure("provider_rate_limited"))

    disposition = await execution(
        repository,
        loader,
        analyzer=FakeAnalyzer(valid_mapping()),
        transcriber=transcriber,
    ).execute(repository.job.id)

    assert disposition is AnalysisDisposition.ACK
    assert repository.job.status == "retry_wait"
    assert repository.failures[0]["error_code"] == "provider_rate_limited"
    assert repository.failures[0]["retryable"] is True
    assert repository.failures[0]["retry_at"] is not None
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_invalid_model_evidence_fails_without_retry(tmp_path: Path) -> None:
    repository = FakeRepository(running_job())
    loader = FakeLoader(tmp_path)
    invalid = valid_mapping()
    invalid["summary"] = {
        "text": "invented",
        "evidence_segment_ids": ["not-real"],
    }

    disposition = await execution(
        repository, loader, analyzer=FakeAnalyzer(invalid)
    ).execute(repository.job.id)

    assert disposition is AnalysisDisposition.ACK
    assert repository.job.status == "failed"
    assert repository.failures[0]["error_code"] == "invalid_model_output"
    assert repository.failures[0]["retryable"] is False
    assert loader.cleaned is True
