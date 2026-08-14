from __future__ import annotations

from dataclasses import replace

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    CancelAnalysis,
    GetAnalysis,
)
from app.domain.analysis import (
    AnalysisMedia,
    AnalysisStatus,
    EvidenceSummary,
    ProductionAdvice,
    Shot,
    VideoAnalysisResult,
)
from tests.unit.application.analysis.fakes import FakeRepository
from tests.unit.application.analysis.test_create_analysis import (
    JOB_ID,
    NOW,
    OWNER,
    artifact,
    creator,
)

RESULT = VideoAnalysisResult(
    language="zh-CN",
    title="可验证视觉分析",
    summary=EvidenceSummary(text="摘要", evidence_shot_ids=("shot-1",)),
    media=AnalysisMedia(duration_ms=1_000, container="mp4", size_bytes=100),
    shot_count=1,
    shots=(
        Shot(
            id="shot-1",
            index=1,
            start_ms=0,
            end_ms=1_000,
            representative_frame_ms=500,
            description="开场画面",
            transition_in="none",
            shot_size="wide",
            camera_motion="static",
            narrative_function="建立故事空间。",
            highlight_score=3,
            visual_tags=("开场",),
            asset_ids=(),
        ),
    ),
    highlights=(),
    assets=(),
    production_advice=ProductionAdvice(
        summary="优先还原开场镜头。",
        priority_shot_ids=("shot-1",),
        recommended_extensions=("镜头 Prompt",),
    ),
)


async def saved_job(repository: FakeRepository) -> None:
    source = artifact()
    repository.artifacts[source.id] = source
    await creator(repository)(
        source.download_id, OWNER, "request", "director-breakdown", "zh-CN"
    )


@pytest.mark.asyncio
async def test_get_requires_owner_and_returns_result_only_for_success() -> None:
    repository = FakeRepository()
    await saved_job(repository)
    repository.jobs[JOB_ID] = replace(
        repository.jobs[JOB_ID],
        status="succeeded",
        progress=100,
        finished_at=NOW,
    )
    repository.results[JOB_ID] = RESULT

    view = await GetAnalysis(repository)(JOB_ID, OWNER)
    assert view.status is AnalysisStatus.SUCCEEDED
    assert view.result == RESULT
    assert not hasattr(view, "artifact_id")

    with pytest.raises(AnalysisApplicationError) as caught:
        await GetAnalysis(repository)(JOB_ID, "c" * 64)
    assert caught.value.code is AnalysisApplicationErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_success_without_atomic_result_is_internal_error() -> None:
    repository = FakeRepository()
    await saved_job(repository)
    repository.jobs[JOB_ID] = replace(repository.jobs[JOB_ID], status="succeeded")

    with pytest.raises(AnalysisApplicationError) as caught:
        await GetAnalysis(repository)(JOB_ID, OWNER)
    assert caught.value.code is AnalysisApplicationErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_cancel_is_owner_scoped_and_maps_terminal_conflict() -> None:
    repository = FakeRepository()
    await saved_job(repository)
    cancel = CancelAnalysis(repository, now=lambda: NOW)

    cancelled = await cancel(JOB_ID, OWNER)
    assert cancelled.status is AnalysisStatus.CANCELLED

    repository.jobs[JOB_ID] = replace(repository.jobs[JOB_ID], status="succeeded")
    with pytest.raises(AnalysisApplicationError) as conflict:
        await cancel(JOB_ID, OWNER)
    assert conflict.value.code is AnalysisApplicationErrorCode.INVALID_STATE

    with pytest.raises(AnalysisApplicationError) as hidden:
        await cancel(JOB_ID, "d" * 64)
    assert hidden.value.code is AnalysisApplicationErrorCode.NOT_FOUND
