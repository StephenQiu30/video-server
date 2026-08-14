from dataclasses import replace
from pathlib import Path

import pytest
from app.application.analysis_execution import (
    AnalysisDisposition,
    ScreenplaySceneSource,
)
from app.domain.analysis import ScreenplayAnalysisResult

from .fakes import FakeLoader
from .fixtures import valid_screenplay_mapping
from .screenplay_fakes import (
    SCREENPLAY_TEXT,
    FakeScreenplayAnalyzer,
    FakeScreenplayLoader,
    ScreenplayRepository,
    build_screenplay_execution,
    screenplay_job_and_source,
)


@pytest.mark.asyncio
async def test_screenplay_analysis_publishes_grounded_result(tmp_path: Path) -> None:
    job, source = screenplay_job_and_source()
    repository = ScreenplayRepository(job, source)
    loader = FakeScreenplayLoader(tmp_path / "screenplay")
    analyzer = FakeScreenplayAnalyzer(valid_screenplay_mapping())

    disposition = await build_screenplay_execution(
        repository, FakeLoader(tmp_path / "video"), loader, analyzer
    ).execute(job.id, job.run_id, job.run_no, job.version)

    assert disposition is AnalysisDisposition.ACK
    assert isinstance(repository.published[0], ScreenplayAnalysisResult)
    assert [stage for stage, _ in repository.heartbeats] == [
        "preparing",
        "analyzing",
        "validating",
    ]
    assert analyzer.requests[0].source_scene_ids == ("scene-1",)
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_screenplay_rewrite_stays_unsupported_without_model_call(
    tmp_path: Path,
) -> None:
    job, source = screenplay_job_and_source()
    job = replace(job, result_contract="screenplay-rewrite")
    repository = ScreenplayRepository(job, source)
    loader = FakeScreenplayLoader(tmp_path / "screenplay")
    analyzer = FakeScreenplayAnalyzer(valid_screenplay_mapping())

    await build_screenplay_execution(
        repository, FakeLoader(tmp_path / "video"), loader, analyzer
    ).execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.failures[0]["error_code"] == "analysis_cli_unsupported"
    assert analyzer.requests == []
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_screenplay_over_single_call_limit_fails_before_download(
    tmp_path: Path,
) -> None:
    job, source = screenplay_job_and_source(character_count=len(SCREENPLAY_TEXT) + 1)
    repository = ScreenplayRepository(job, source)
    loader = FakeScreenplayLoader(tmp_path / "screenplay")

    await build_screenplay_execution(
        repository,
        FakeLoader(tmp_path / "video"),
        loader,
        FakeScreenplayAnalyzer(valid_screenplay_mapping()),
        maximum=len(SCREENPLAY_TEXT),
    ).execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.failures[0]["error_code"] == "analysis_resource_limit"
    assert repository.failures[0]["retryable"] is False
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_screenplay_scene_limit_fails_before_download(tmp_path: Path) -> None:
    job, source = screenplay_job_and_source(character_count=121)
    source = replace(
        source,
        scenes=tuple(
            ScreenplaySceneSource(f"scene-{index:04d}-{'a' * 12}", index, index + 1)
            for index in range(121)
        ),
    )
    repository = ScreenplayRepository(job, source)
    loader = FakeScreenplayLoader(tmp_path / "screenplay")

    await build_screenplay_execution(
        repository,
        FakeLoader(tmp_path / "video"),
        loader,
        FakeScreenplayAnalyzer(valid_screenplay_mapping()),
    ).execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.failures[0]["error_code"] == "analysis_resource_limit"
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_screenplay_unknown_evidence_retries_as_invalid_output(
    tmp_path: Path,
) -> None:
    job, source = screenplay_job_and_source()
    repository = ScreenplayRepository(job, source)
    payload = valid_screenplay_mapping()
    strength = payload["strengths"]
    assert isinstance(strength, list) and isinstance(strength[0], dict)
    strength[0]["evidence_scene_ids"] = ["invented-scene"]

    await build_screenplay_execution(
        repository,
        FakeLoader(tmp_path / "video"),
        FakeScreenplayLoader(tmp_path / "screenplay"),
        FakeScreenplayAnalyzer(payload),
    ).execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.failures[0]["error_code"] == "invalid_model_output"
    assert repository.failures[0]["retryable"] is True
