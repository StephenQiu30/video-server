from __future__ import annotations

from pathlib import Path

import pytest
from app.application.downloads import (
    MediaInspectionAuthRequired,
    MediaInspectionTemporarilyUnavailable,
    RunnerInspection,
)
from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.infrastructure.media_runner import MediaRunnerRouter
from app.infrastructure.media_runner_models import (
    MediaRunnerClientError,
    RunnerArtifact,
)


class FakeClient:
    def __init__(self, context: ProviderAccessContextRef) -> None:
        self.context = context
        self.inspect_error: Exception | None = None
        self.download_error: Exception | None = None
        self.inspected: list[str] = []
        self.downloaded: list[str] = []
        self.context_requests: list[tuple[str, ...]] = []

    async def context_for_provider(self, provider_key: str) -> ProviderAccessContextRef:
        self.context_requests.append((provider_key,))
        return self.context

    async def contexts_for_providers(
        self, provider_keys: tuple[str, ...]
    ) -> tuple[ProviderAccessContextRef, ...]:
        self.context_requests.append(provider_keys)
        return (self.context,)

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
        if self.download_error is not None:
            raise self.download_error
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


async def test_configured_youtube_routes_directly_to_operator_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    result = await router.inspect("https://www.youtube.com/watch?v=owned")

    assert result.access_context.access_mode is ProviderAccessMode.OPERATOR_MANAGED
    assert anonymous.inspected == []
    assert operator.inspected == ["https://www.youtube.com/watch?v=owned"]


async def test_operator_diagnosis_is_authoritative_without_anonymous_attempt() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    operator.inspect_error = MediaInspectionTemporarilyUnavailable()
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionTemporarilyUnavailable) as captured:
        await router.inspect("https://www.youtube.com/watch?v=owned")

    assert captured.value.access_mode is ProviderAccessMode.OPERATOR_MANAGED
    assert anonymous.inspected == []


async def test_configured_xiaohongshu_routes_directly_to_operator_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED, "xiaohongshu"))
    router = MediaRunnerRouter(  # type: ignore[arg-type]
        anonymous,
        {"xiaohongshu": operator},
    )

    result = await router.inspect(
        "https://www.xiaohongshu.com/explore/6411cf99000000001300b6d9"
    )

    assert result.access_context.provider_key == "xiaohongshu"
    assert anonymous.inspected == []


async def test_unconfigured_provider_uses_its_declared_anonymous_mode() -> None:
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


async def test_configured_instagram_routes_directly_to_operator_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED, "instagram"))
    router = MediaRunnerRouter(anonymous, {"instagram": operator})  # type: ignore[arg-type]

    result = await router.inspect("https://www.instagram.com/reel/owned/")

    assert result.access_context.provider_key == "instagram"
    assert anonymous.inspected == []
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


async def test_download_never_changes_the_frozen_access_context() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.download_error = MediaRunnerClientError("credential_required", 422)
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaRunnerClientError) as captured:
        await router.download(
            "task-1",
            "https://www.youtube.com/watch?v=owned",
            object(),  # type: ignore[arg-type]
            expected_provider_media_id="owned",
            expected_extractor_key="Youtube",
            access_context=anonymous.context,
        )

    assert captured.value.code == "credential_required"
    assert anonymous.downloaded == ["task-1"]
    assert operator.context_requests == []
    assert operator.downloaded == []


async def test_download_keeps_anonymous_error_when_operator_is_not_configured() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.download_error = MediaRunnerClientError("credential_required", 422)
    router = MediaRunnerRouter(anonymous)

    with pytest.raises(MediaRunnerClientError) as captured:
        await router.download(
            "task-1",
            "https://www.youtube.com/watch?v=owned",
            object(),  # type: ignore[arg-type]
            expected_provider_media_id="owned",
            expected_extractor_key="Youtube",
            access_context=anonymous.context,
        )

    assert captured.value.code == "credential_required"


async def test_context_batch_resolves_anonymous_and_operator_routes_once() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    resolved = await router.contexts_for_providers(
        {
            "generic": ProviderAccessMode.ANONYMOUS,
            "youtube": ProviderAccessMode.OPERATOR_MANAGED,
        }
    )

    assert resolved == {"generic": anonymous.context, "youtube": operator.context}
    assert anonymous.context_requests == [("generic",)]
    assert operator.context_requests == [("youtube",)]


async def test_context_batch_isolates_one_unavailable_operator_runner() -> None:
    class UnavailableClient(FakeClient):
        async def contexts_for_providers(
            self, provider_keys: tuple[str, ...]
        ) -> tuple[ProviderAccessContextRef, ...]:
            self.context_requests.append(provider_keys)
            raise MediaRunnerClientError("runner_unavailable", 503)

    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = UnavailableClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    resolved = await router.contexts_for_providers(
        {
            "generic": ProviderAccessMode.ANONYMOUS,
            "youtube": ProviderAccessMode.OPERATOR_MANAGED,
        }
    )

    assert resolved == {"generic": anonymous.context}


def context(
    mode: ProviderAccessMode, provider: str = "youtube"
) -> ProviderAccessContextRef:
    operator = mode is ProviderAccessMode.OPERATOR_MANAGED
    return ProviderAccessContextRef(
        provider_key=provider if operator else "generic",
        profile_version=provider if operator else "default",
        access_mode=mode,
        credential_version_id="browser" if operator else None,
        egress_affinity_id=f"provider:{provider}" if operator else "default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit="5d6b8c8",
    )
