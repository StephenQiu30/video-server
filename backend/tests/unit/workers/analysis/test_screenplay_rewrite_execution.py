from pathlib import Path

import pytest
from app.application.analysis_execution import AnalysisDisposition
from app.domain.analysis import ScreenplayRewriteResult

from .screenplay_rewrite_fakes import build_rewrite_execution


@pytest.mark.asyncio
async def test_rewrite_publishes_complete_ordered_source_bound_result(
    tmp_path: Path,
) -> None:
    execution, repository, loader, analyzer, resolver = build_rewrite_execution(
        tmp_path
    )
    job = repository.job

    disposition = await execution.execute(job.id, job.run_id, job.run_no, job.version)

    assert disposition is AnalysisDisposition.ACK
    result = repository.published[0]
    assert isinstance(result, ScreenplayRewriteResult)
    assert len(result.chunks) == len(analyzer.chunk_requests) > 1
    assert [
        (item.source_scene_id, item.part_no, item.source_sha256)
        for item in result.chunks
    ] == [
        (item.source_scene_id, item.part_no, item.source_sha256)
        for item in analyzer.chunk_requests
    ]
    assert result.source_scene_count == result.output_scene_count == 1
    assert result.target_language == "en-US"
    assert analyzer.glossary_requests[0].screenplay_text
    assert resolver.calls == 1
    assert loader.cleaned is True
    assert [stage for stage, _ in repository.heartbeats] == [
        "preparing",
        "analyzing",
        "analyzing",
        *("analyzing" for _ in analyzer.chunk_requests),
        "validating",
    ]


@pytest.mark.asyncio
async def test_rewrite_identity_mismatch_retries_without_partial_publish(
    tmp_path: Path,
) -> None:
    execution, repository, loader, analyzer, _ = build_rewrite_execution(tmp_path)
    analyzer.invalid_call = 2
    job = repository.job

    await execution.execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.published == []
    assert repository.failures[0]["error_code"] == "invalid_model_output"
    assert repository.failures[0]["retryable"] is True
    assert len(analyzer.chunk_requests) == 2
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_rewrite_output_limit_fails_without_partial_publish(
    tmp_path: Path,
) -> None:
    execution, repository, loader, analyzer, _ = build_rewrite_execution(
        tmp_path, max_output=10
    )
    job = repository.job

    await execution.execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.published == []
    assert repository.failures[0]["error_code"] == "analysis_resource_limit"
    assert repository.failures[0]["retryable"] is False
    assert len(analyzer.chunk_requests) == 1
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_rewrite_glossary_drift_retries_without_partial_publish(
    tmp_path: Path,
) -> None:
    execution, repository, loader, analyzer, _ = build_rewrite_execution(tmp_path)
    analyzer.omit_glossary_target = True
    job = repository.job

    await execution.execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.published == []
    assert repository.failures[0]["error_code"] == "invalid_model_output"
    assert repository.failures[0]["retryable"] is True
    assert len(analyzer.chunk_requests) > 1
    assert loader.cleaned is True


@pytest.mark.asyncio
async def test_rewrite_chunk_limit_fails_before_model_resolution(
    tmp_path: Path,
) -> None:
    execution, repository, loader, analyzer, resolver = build_rewrite_execution(
        tmp_path, maximum=10, max_chunks=1
    )
    job = repository.job

    await execution.execute(job.id, job.run_id, job.run_no, job.version)

    assert repository.published == []
    assert repository.failures[0]["error_code"] == "analysis_resource_limit"
    assert resolver.calls == 0
    assert analyzer.glossary_requests == []
    assert loader.cleaned is True
