from __future__ import annotations

from pathlib import Path

import pytest
from app.application.downloads import (
    MediaInspectionAuthRequired,
    MediaInspectionLinkUnavailable,
    MediaInspectionRateLimited,
    MediaInspectionSessionExpired,
    MediaInspectionTemporarilyUnavailable,
    RunnerInspection,
)
from app.application.downloads.errors import MediaInspectionFormatUnavailable
from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.infrastructure.media_runner import MediaRunnerRouter
from app.infrastructure.media_runner_models import RunnerArtifact


class FakeClient:
    def __init__(self, context: ProviderAccessContextRef) -> None:
        self.context = context
        self.inspect_error: Exception | None = None
        self.inspected: list[str] = []
        self.downloaded: list[str] = []

    async def inspect(self, url: str) -> RunnerInspection:
        self.inspected.append(url)
        if self.inspect_error is not None:
            raise self.inspect_error
        return RunnerInspection(
            extractor_key="Youtube",
            provider_media_id="owned",
            title="Owned",
            duration_seconds=30,
            formats=(),
            access_context=self.context,
        )

    async def download(self, task_id: str, *_args, **_kwargs) -> RunnerArtifact:
        self.downloaded.append(task_id)
        return RunnerArtifact(
            task_id=task_id,
            workspace=Path("/work") / task_id,
            artifact=Path("/work") / task_id / "artifact.mp4",
            size_bytes=1,
            sha256="a" * 64,
            duration_seconds=30,
            container="mp4",
            video_streams=1,
            audio_streams=1,
        )

    async def status(self, _task_id):
        raise AssertionError("not used")

    async def cancel(self, _task_id):
        raise AssertionError("not used")

    async def close(self) -> None:
        return None


async def test_youtube_access_failure_falls_back_to_operator_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionAuthRequired()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    result = await router.inspect("https://www.youtube.com/watch?v=owned")

    assert result.access_context.access_mode is ProviderAccessMode.OPERATOR_MANAGED
    assert len(anonymous.inspected) == len(operator.inspected) == 1


async def test_youtube_link_unavailable_falls_back_to_operator_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionLinkUnavailable()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    result = await router.inspect("https://www.youtube.com/watch?v=owned")

    assert result.access_context.access_mode is ProviderAccessMode.OPERATOR_MANAGED
    assert len(anonymous.inspected) == len(operator.inspected) == 1


async def test_operator_failure_preserves_anonymous_diagnosis() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionAuthRequired()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    operator.inspect_error = MediaInspectionTemporarilyUnavailable()
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionAuthRequired) as captured:
        await router.inspect("https://www.youtube.com/watch?v=owned")

    assert captured.value.access_mode is ProviderAccessMode.ANONYMOUS


async def test_operator_session_expiry_replaces_anonymous_diagnosis() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionAuthRequired()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    operator.inspect_error = MediaInspectionSessionExpired()
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionSessionExpired) as captured:
        await router.inspect("https://www.youtube.com/watch?v=owned")

    assert captured.value.access_mode is ProviderAccessMode.OPERATOR_MANAGED


async def test_operator_link_unavailable_replaces_anonymous_degradation() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionTemporarilyUnavailable()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED, "xiaohongshu"))
    operator.inspect_error = MediaInspectionLinkUnavailable()
    router = MediaRunnerRouter(  # type: ignore[arg-type]
        anonymous,
        {"xiaohongshu": operator},
    )

    with pytest.raises(MediaInspectionLinkUnavailable) as captured:
        await router.inspect(
            "https://www.xiaohongshu.com/explore/6411cf99000000001300b6d9"
        )

    assert captured.value.access_mode is ProviderAccessMode.OPERATOR_MANAGED


async def test_non_fallback_failure_does_not_consume_operator_session() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionRateLimited()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionRateLimited) as captured:
        await router.inspect("https://www.youtube.com/watch?v=owned")

    assert captured.value.access_mode is ProviderAccessMode.ANONYMOUS
    assert operator.inspected == []


async def test_unconfigured_provider_does_not_receive_operator_session() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionAuthRequired()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionAuthRequired) as captured:
        await router.inspect("https://www.bilibili.com/video/BV1xx")

    assert captured.value.access_mode is ProviderAccessMode.ANONYMOUS
    assert operator.inspected == []


async def test_tiktok_access_failure_never_uses_configured_operator() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionTemporarilyUnavailable()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED, "tiktok"))
    router = MediaRunnerRouter(anonymous, {"tiktok": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionTemporarilyUnavailable):
        await router.inspect("https://www.tiktok.com/@creator/video/123")

    assert operator.inspected == []


async def test_instagram_video_only_metadata_falls_back_to_operator_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionFormatUnavailable()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED, "instagram"))
    router = MediaRunnerRouter(anonymous, {"instagram": operator})  # type: ignore[arg-type]

    result = await router.inspect("https://www.instagram.com/reel/owned/")

    assert result.access_context.provider_key == "instagram"
    assert operator.inspected == ["https://www.instagram.com/reel/owned/"]


async def test_download_routes_frozen_context_to_matching_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    await router.download(
        "task-1",
        "https://www.youtube.com/watch?v=owned",
        object(),  # type: ignore[arg-type]
        expected_provider_media_id="owned",
        expected_extractor_key="Youtube",
        access_context=operator.context,
    )

    assert anonymous.downloaded == []
    assert operator.downloaded == ["task-1"]


def context(
    mode: ProviderAccessMode, provider: str = "youtube"
) -> ProviderAccessContextRef:
    operator = mode is ProviderAccessMode.OPERATOR_MANAGED
    return ProviderAccessContextRef(
        provider_key=provider if operator else "generic",
        profile_version=f"{provider}-v2" if operator else "1",
        access_mode=mode,
        credential_version_id="version-1" if operator else None,
        egress_affinity_id=f"provider:{provider}" if operator else "default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit="5d6b8c8",
    )
