from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    AnalysisJobSnapshot,
    RetryAnalysis,
)
from tests.unit.application.analysis.fakes import FakeRepository

NOW = datetime(2026, 8, 10, 10, tzinfo=UTC)
JOB_ID = UUID("11111111-1111-4111-8111-111111111111")
RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
OWNER = "a" * 64


def terminal_job(status: str = "failed") -> AnalysisJobSnapshot:
    return AnalysisJobSnapshot(
        id=JOB_ID,
        artifact_id=uuid4(),
        owner_hash=OWNER,
        request_fingerprint="b" * 64,
        input_sha256="c" * 64,
        skill_id="director-breakdown",
        skill_instructions="固定分析指令",
        skill_instructions_sha256=hashlib.sha256("固定分析指令".encode()).hexdigest(),
        output_language="zh-CN",
        custom_prompt="固定观察重点",
        status=status,
        stage=None,
        progress=100 if status == "succeeded" else 20,
        attempt=2,
        max_attempts=3,
        version=5,
        run_id=uuid4(),
        run_no=1,
        run_trigger="initial",
        lease_owner=None,
        lease_expires_at=None,
        heartbeat_at=None,
        started_at=NOW,
        retry_at=None,
        finished_at=NOW,
        error_code=None if status == "succeeded" else "analysis_cli_failed",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_retry_keeps_job_and_idempotently_creates_next_run() -> None:
    repository = FakeRepository()
    repository.jobs[JOB_ID] = terminal_job()
    ids = iter((RUN_ID, uuid4(), uuid4(), uuid4()))
    retry = RetryAnalysis(repository, now=lambda: NOW, new_id=lambda: next(ids))

    first = await retry(JOB_ID, OWNER, "retry-key")
    replay = await retry(JOB_ID, OWNER, "retry-key")

    assert first.id == replay.id == JOB_ID
    assert first.run_id == replay.run_id == RUN_ID
    assert (first.run_no, first.run_trigger, first.attempt) == (
        2,
        "manual_retry",
        0,
    )
    assert repository.outbox_events == 1


@pytest.mark.asyncio
async def test_rerun_trigger_and_active_or_foreign_rejection() -> None:
    repository = FakeRepository()
    repository.jobs[JOB_ID] = terminal_job("succeeded")
    rerun = await RetryAnalysis(repository, now=lambda: NOW, new_id=uuid4)(
        JOB_ID, OWNER, "rerun-key"
    )
    assert rerun.run_trigger == "manual_rerun"

    repository.jobs[JOB_ID] = replace(terminal_job(), status="running")
    with pytest.raises(AnalysisApplicationError) as active:
        await RetryAnalysis(repository, now=lambda: NOW, new_id=uuid4)(
            JOB_ID, OWNER, "active-key"
        )
    assert active.value.code is AnalysisApplicationErrorCode.ALREADY_ACTIVE

    with pytest.raises(AnalysisApplicationError) as foreign:
        await RetryAnalysis(repository, now=lambda: NOW, new_id=uuid4)(
            JOB_ID, "d" * 64, "foreign-key"
        )
    assert foreign.value.code is AnalysisApplicationErrorCode.NOT_FOUND
