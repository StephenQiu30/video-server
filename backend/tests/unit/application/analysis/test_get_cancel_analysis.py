from __future__ import annotations

from dataclasses import replace

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    CancelAnalysis,
    GetAnalysis,
)
from app.domain.analysis import AnalysisStatus
from tests.unit.application.analysis.fakes import FakeRepository
from tests.unit.application.analysis.test_create_analysis import (
    JOB_ID,
    NOW,
    OWNER,
    artifact,
    creator,
)

RESULT = {
    "schema_version": "analysis.v1",
    "language": "zh-CN",
    "title": "可验证摘要",
    "summary": {"text": "摘要", "evidence_segment_ids": ["s1"]},
    "key_points": [{"text": "观点", "evidence_segment_ids": ["s1"]}],
    "action_items": [],
    "chapters": [
        {
            "title": "章节",
            "start_ms": 0,
            "end_ms": 1000,
            "summary": "章节摘要",
            "evidence_segment_ids": ["s1"],
        }
    ],
    "mind_map": {
        "id": "root",
        "title": "主题",
        "summary": None,
        "start_ms": 0,
        "evidence_segment_ids": ["s1"],
        "children": [],
    },
}


async def saved_job(repository: FakeRepository) -> None:
    source = artifact()
    repository.artifacts[source.id] = source
    await creator(repository)(
        source.download_id, OWNER, "request", "standard-v1", "zh-CN"
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
