from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    AnalysisArtifactSnapshot,
    CreateAnalysis,
)
from app.domain.analysis import AnalysisStatus
from tests.unit.application.analysis.fakes import (
    FakeFingerprinter,
    FakeRepository,
    FakeSkillCatalog,
)

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)
OWNER = "a" * 64
ARTIFACT_ID = UUID("11111111-1111-4111-8111-111111111111")
JOB_ID = UUID("22222222-2222-4222-8222-222222222222")
RUN_ID = UUID("22222222-2222-4222-8222-222222222223")
EVENT_ID = UUID("33333333-3333-4333-8333-333333333333")
DOWNLOAD_ID = UUID("44444444-4444-4444-8444-444444444444")


def artifact(**changes: object) -> AnalysisArtifactSnapshot:
    value = AnalysisArtifactSnapshot(
        id=ARTIFACT_ID,
        download_id=DOWNLOAD_ID,
        owner_hash=OWNER,
        download_status="succeeded",
        sha256="b" * 64,
        expires_at=NOW + timedelta(hours=1),
    )
    return replace(value, **changes)


def creator(repository: FakeRepository) -> CreateAnalysis:
    ids = iter((JOB_ID, RUN_ID, EVENT_ID, *(uuid4() for _ in range(20))))
    return CreateAnalysis(
        repository=repository,
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=lambda: next(ids),
        max_attempts=3,
        skill_catalog=FakeSkillCatalog(),
    )


@pytest.mark.asyncio
async def test_create_fails_before_persistence_when_analysis_is_disabled() -> None:
    repository = FakeRepository()
    create = CreateAnalysis(
        repository=repository,
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=uuid4,
        max_attempts=3,
        skill_catalog=FakeSkillCatalog(),
        enabled=False,
    )

    with pytest.raises(AnalysisApplicationError) as caught:
        await create(DOWNLOAD_ID, OWNER, "request-1", "director-breakdown", "zh-CN")

    assert caught.value.code is AnalysisApplicationErrorCode.SERVICE_UNAVAILABLE
    assert repository.commands == []


@pytest.mark.asyncio
async def test_create_persists_job_and_replays_the_same_idempotency_key() -> None:
    repository = FakeRepository()
    repository.artifacts[ARTIFACT_ID] = artifact()
    create = creator(repository)

    first = await create(DOWNLOAD_ID, OWNER, "request-1", "director-breakdown", "zh-CN")
    replay = await create(
        DOWNLOAD_ID, OWNER, "request-1", "director-breakdown", "zh-CN"
    )

    assert first.id == replay.id == JOB_ID
    assert first.status is AnalysisStatus.QUEUED
    assert repository.outbox_events == 1
    command = repository.commands[0]
    assert command.input_sha256 == "b" * 64
    assert command.outbox_event_id == EVENT_ID
    assert command.outbox_event_type == "analysis.requested"


@pytest.mark.asyncio
async def test_create_normalizes_and_fingerprints_custom_prompt() -> None:
    repository = FakeRepository()
    repository.artifacts[ARTIFACT_ID] = artifact()
    create = creator(repository)

    await create(
        DOWNLOAD_ID,
        OWNER,
        "request-1",
        "highlights",
        "zh-CN",
        "  重点识别产品演示。  ",
    )

    assert repository.commands[0].skill_id == "highlights"
    assert repository.commands[0].skill_instructions == "高光提炼完整指令"
    assert repository.commands[0].custom_prompt == "重点识别产品演示。"


@pytest.mark.asyncio
async def test_create_rejects_oversized_custom_prompt() -> None:
    repository = FakeRepository()
    repository.artifacts[ARTIFACT_ID] = artifact()
    create = creator(repository)

    with pytest.raises(AnalysisApplicationError) as caught:
        await create(
            DOWNLOAD_ID,
            OWNER,
            "request-1",
            "director-breakdown",
            "zh-CN",
            "x" * 4_001,
        )

    assert caught.value.code is AnalysisApplicationErrorCode.INVALID_REQUEST


@pytest.mark.asyncio
async def test_create_requires_owned_succeeded_unexpired_artifact() -> None:
    repository = FakeRepository()
    create = creator(repository)

    for value, expected in (
        (artifact(owner_hash="c" * 64), AnalysisApplicationErrorCode.NOT_FOUND),
        (
            artifact(download_status="failed"),
            AnalysisApplicationErrorCode.ARTIFACT_NOT_READY,
        ),
        (
            artifact(expires_at=NOW),
            AnalysisApplicationErrorCode.RESOURCE_EXPIRED,
        ),
    ):
        repository.artifacts[ARTIFACT_ID] = value
        with pytest.raises(AnalysisApplicationError) as caught:
            await create(
                DOWNLOAD_ID,
                OWNER,
                "request",
                "director-breakdown",
                "zh-CN",
            )
        assert caught.value.code is expected


@pytest.mark.asyncio
async def test_idempotency_key_cannot_be_reused_for_another_input() -> None:
    repository = FakeRepository()
    second_artifact, second_download = uuid4(), uuid4()
    repository.artifacts[ARTIFACT_ID] = artifact()
    repository.artifacts[second_artifact] = replace(
        artifact(),
        id=second_artifact,
        download_id=second_download,
        sha256="c" * 64,
    )
    create = creator(repository)

    await create(DOWNLOAD_ID, OWNER, "same-key", "director-breakdown", "zh-CN")
    with pytest.raises(AnalysisApplicationError) as caught:
        await create(
            second_download,
            OWNER,
            "same-key",
            "director-breakdown",
            "zh-CN",
        )
    assert caught.value.code is AnalysisApplicationErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.asyncio
async def test_create_validates_owner_key_skill_and_language() -> None:
    repository = FakeRepository()
    repository.artifacts[ARTIFACT_ID] = artifact()
    create = creator(repository)

    invalid = (
        ("owner", "key", "director-breakdown", "zh-CN"),
        (OWNER, "", "director-breakdown", "zh-CN"),
        (OWNER, "key", "", "zh-CN"),
        (OWNER, "key", "director-breakdown", ""),
    )
    for owner, key, skill_id, language in invalid:
        with pytest.raises(AnalysisApplicationError) as caught:
            await create(DOWNLOAD_ID, owner, key, skill_id, language)
        assert caught.value.code is AnalysisApplicationErrorCode.INVALID_REQUEST
