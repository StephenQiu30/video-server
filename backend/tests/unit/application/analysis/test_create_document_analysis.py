from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    AnalysisDocumentSnapshot,
    CreateDocumentAnalysis,
)
from app.domain.analysis import (
    AnalysisInputKind,
    AnalysisResultContract,
    AnalysisStatus,
)
from tests.unit.application.analysis.fakes import (
    FakeFingerprinter,
    FakeRepository,
    FakeSkillCatalog,
)

NOW = datetime(2026, 8, 14, 12, tzinfo=UTC)
OWNER = "a" * 64
DOCUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")
JOB_ID = UUID("22222222-2222-4222-8222-222222222222")
RUN_ID = UUID("22222222-2222-4222-8222-222222222223")
EVENT_ID = UUID("33333333-3333-4333-8333-333333333333")


def document(**changes: object) -> AnalysisDocumentSnapshot:
    value = AnalysisDocumentSnapshot(
        id=DOCUMENT_ID,
        owner_hash=OWNER,
        status="ready",
        text_sha256="b" * 64,
        normalized_status="ready",
        normalized_sha256="b" * 64,
    )
    return replace(value, **changes)


def creator(repository: FakeRepository, *, enabled: bool = True):
    ids = iter((JOB_ID, RUN_ID, EVENT_ID, *(uuid4() for _ in range(20))))
    return CreateDocumentAnalysis(
        repository=repository,
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=lambda: next(ids),
        max_attempts=3,
        skill_catalog=FakeSkillCatalog(),
        enabled=enabled,
    )


@pytest.mark.asyncio
async def test_document_analysis_is_disabled_by_default() -> None:
    repository = FakeRepository()
    create = CreateDocumentAnalysis(
        repository=repository,
        fingerprinter=FakeFingerprinter(),
        now=lambda: NOW,
        new_id=uuid4,
        max_attempts=3,
        skill_catalog=FakeSkillCatalog(),
    )

    with pytest.raises(AnalysisApplicationError) as caught:
        await create(DOCUMENT_ID, OWNER, "request-1", "screenplay-analysis", "zh-CN")

    assert caught.value.code is AnalysisApplicationErrorCode.SERVICE_UNAVAILABLE
    assert repository.commands == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("skill_id", "contract"),
    (
        ("screenplay-analysis", AnalysisResultContract.SCREENPLAY_ANALYSIS),
        ("screenplay-rewrite", AnalysisResultContract.SCREENPLAY_REWRITE),
    ),
)
async def test_create_document_analysis_snapshots_source_and_skill(
    skill_id: str, contract: AnalysisResultContract
) -> None:
    repository = FakeRepository()
    repository.documents[DOCUMENT_ID] = document()
    create = creator(repository)

    view = await create(DOCUMENT_ID, OWNER, "request-1", skill_id, "en-US")

    assert view.id == JOB_ID
    assert view.status is AnalysisStatus.QUEUED
    assert view.input_kind is AnalysisInputKind.SCREENPLAY
    assert view.result_contract is contract
    command = repository.commands[0]
    assert command.artifact_id is None
    assert command.document_id == DOCUMENT_ID
    assert command.input_sha256 == "b" * 64
    assert command.skill_instructions_sha256 == "f" * 64
    assert repository.outbox_events == 1


@pytest.mark.asyncio
async def test_create_document_analysis_replays_idempotently() -> None:
    repository = FakeRepository()
    repository.documents[DOCUMENT_ID] = document()
    create = creator(repository)

    first = await create(
        DOCUMENT_ID, OWNER, "request-1", "screenplay-analysis", "zh-CN"
    )
    replay = await create(
        DOCUMENT_ID, OWNER, "request-1", "screenplay-analysis", "zh-CN"
    )

    assert first.id == replay.id == JOB_ID
    assert repository.outbox_events == 1


@pytest.mark.asyncio
async def test_create_document_analysis_validates_owner_state_hash_and_language() -> (
    None
):
    cases = (
        (
            document(owner_hash="c" * 64),
            "zh-CN",
            AnalysisApplicationErrorCode.NOT_FOUND,
        ),
        (
            document(status="failed"),
            "zh-CN",
            AnalysisApplicationErrorCode.ARTIFACT_NOT_READY,
        ),
        (
            document(normalized_sha256="c" * 64),
            "zh-CN",
            AnalysisApplicationErrorCode.ARTIFACT_NOT_READY,
        ),
        (document(), "fr-FR", AnalysisApplicationErrorCode.INVALID_REQUEST),
    )
    for source, language, expected in cases:
        repository = FakeRepository()
        repository.documents[DOCUMENT_ID] = source
        with pytest.raises(AnalysisApplicationError) as caught:
            await creator(repository)(
                DOCUMENT_ID,
                OWNER,
                "request-1",
                "screenplay-analysis",
                language,
            )
        assert caught.value.code is expected


@pytest.mark.asyncio
async def test_document_analysis_rejects_video_skill() -> None:
    repository = FakeRepository()
    repository.documents[DOCUMENT_ID] = document()

    with pytest.raises(AnalysisApplicationError) as caught:
        await creator(repository)(
            DOCUMENT_ID, OWNER, "request-1", "director-breakdown", "zh-CN"
        )

    assert caught.value.code is AnalysisApplicationErrorCode.INVALID_REQUEST
