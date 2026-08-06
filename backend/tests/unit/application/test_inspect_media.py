from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.application.downloads import (
    ApplicationError,
    ApplicationErrorCode,
    GetInspection,
    HmacRequestFingerprinter,
    InspectMedia,
    RunnerFormat,
    RunnerInspection,
)
from app.domain.downloads import (
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DownloadPlan,
    DynamicRange,
    FpsBucket,
    ProviderHints,
    VideoCodecFamily,
)
from tests.unit.application.fakes import (
    FakeCipher,
    FakeRepository,
    FakeRunner,
    FakeValidator,
)

NOW = datetime(2026, 8, 6, 9, tzinfo=UTC)
URL = "https://media.example/watch?v=owned"
OWNER = "a" * 64


def plan(height: int = 1080) -> DownloadPlan:
    return DownloadPlan(
        height=height,
        width=1920 if height == 1080 else 1280,
        fps_bucket=FpsBucket.FPS_30,
        dynamic_range=DynamicRange.SDR,
        video_codec_family=VideoCodecFamily.H264,
        audio_codec_family=AudioCodecFamily.AAC,
        audio_language="zh-CN",
        container_preference=ContainerPreference.MP4,
        compatibility_profile=CompatibilityProfile.BALANCED,
        hints=ProviderHints(video_id="137", audio_id="140"),
    )


def runner_result(*, duration: int = 30) -> RunnerInspection:
    return RunnerInspection(
        extractor_key="Controlled",
        provider_media_id="video-1",
        title="Owned video",
        duration_seconds=duration,
        formats=(RunnerFormat("1080p MP4", plan()),),
    )


def use_case(
    repository: FakeRepository,
    result: RunnerInspection,
) -> tuple[InspectMedia, FakeRunner, FakeCipher]:
    runner, cipher = FakeRunner(result), FakeCipher()
    return (
        InspectMedia(
            repository=repository,
            runner=runner,
            url_validator=FakeValidator(),
            url_cipher=cipher,
            fingerprinter=HmacRequestFingerprinter(b"k" * 32),
            now=lambda: NOW,
            new_id=uuid4,
            inspection_ttl=timedelta(minutes=15),
            max_duration_seconds=7_200,
        ),
        runner,
        cipher,
    )


@pytest.mark.asyncio
async def test_inspect_encrypts_url_and_returns_only_semantic_formats() -> None:
    repository = FakeRepository()
    inspect, runner, cipher = use_case(repository, runner_result())

    view = await inspect(URL, OWNER, "inspect-1")

    command = repository.inspection_commands[0]
    assert command.expires_at == NOW + timedelta(minutes=15)
    assert command.url_ciphertext == b"opaque-ciphertext"
    assert URL.encode() not in command.url_ciphertext
    assert runner.seen == cipher.seen == [URL]
    assert not hasattr(command, "url")
    assert not hasattr(view, "url")
    assert URL not in repr(command)
    assert view.formats[0].plan.hints == ProviderHints()
    assert command.formats[0].provider_hints == {
        "video_id": "137",
        "audio_id": "140",
    }


@pytest.mark.asyncio
async def test_inspection_idempotency_replays_and_conflicts() -> None:
    repository = FakeRepository()
    inspect, _, _ = use_case(repository, runner_result())
    first = await inspect(URL, OWNER, "same-key")
    replay = await inspect(URL, OWNER, "same-key")

    assert replay.id == first.id
    with pytest.raises(ApplicationError) as caught:
        await inspect("https://other.example/video", OWNER, "same-key")
    assert caught.value.code is ApplicationErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.asyncio
async def test_invalid_url_never_reaches_runner() -> None:
    repository = FakeRepository()
    inspect, runner, _ = use_case(repository, runner_result())
    unsafe_url = "file:///etc/passwd"

    with pytest.raises(ApplicationError) as caught:
        await inspect(unsafe_url, OWNER, "inspect-1")

    assert caught.value.code is ApplicationErrorCode.INVALID_URL
    assert unsafe_url not in str(caught.value)
    assert runner.seen == []


@pytest.mark.asyncio
async def test_duration_limit_and_empty_formats_are_rejected() -> None:
    repository = FakeRepository()
    too_long, _, _ = use_case(repository, runner_result(duration=7_201))
    with pytest.raises(ApplicationError) as duration_error:
        await too_long(URL, OWNER, "duration")
    assert duration_error.value.code is ApplicationErrorCode.DURATION_LIMIT_EXCEEDED

    empty_result = RunnerInspection("Controlled", "id", "title", 30, ())
    no_formats, _, _ = use_case(repository, empty_result)
    with pytest.raises(ApplicationError) as format_error:
        await no_formats(URL, OWNER, "formats")
    assert format_error.value.code is ApplicationErrorCode.FORMAT_UNAVAILABLE
    assert repository.inspection_commands == []


@pytest.mark.asyncio
async def test_get_inspection_enforces_owner_and_ttl() -> None:
    repository = FakeRepository()
    inspect, _, _ = use_case(repository, runner_result())
    created = await inspect(URL, OWNER, "inspect-1")
    get = GetInspection(repository, now=lambda: NOW)

    assert (await get(created.id, OWNER)).id == created.id
    with pytest.raises(ApplicationError) as foreign:
        await get(created.id, "b" * 64)
    assert foreign.value.code is ApplicationErrorCode.NOT_FOUND

    snapshot = repository.inspections[created.id]
    repository.inspections[created.id] = replace(snapshot, expires_at=NOW, formats=())
    with pytest.raises(ApplicationError) as expired:
        await get(created.id, OWNER)
    assert expired.value.code is ApplicationErrorCode.RESOURCE_EXPIRED
