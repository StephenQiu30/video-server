from __future__ import annotations

from pathlib import Path

import pytest
from app.application.downloads import MediaInspectionAuthRequired, RunnerInspection
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
    router = MediaRunnerRouter(anonymous, operator)  # type: ignore[arg-type]

    result = await router.inspect("https://www.youtube.com/watch?v=owned")

    assert result.access_context.access_mode is ProviderAccessMode.OPERATOR_MANAGED
    assert len(anonymous.inspected) == len(operator.inspected) == 1


async def test_non_youtube_access_failure_does_not_receive_operator_session() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionAuthRequired()
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, operator)  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionAuthRequired):
        await router.inspect("https://www.bilibili.com/video/BV1xx")

    assert operator.inspected == []


async def test_download_routes_frozen_context_to_matching_pool() -> None:
    anonymous = FakeClient(context(ProviderAccessMode.ANONYMOUS))
    operator = FakeClient(context(ProviderAccessMode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, operator)  # type: ignore[arg-type]

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


def context(mode: ProviderAccessMode) -> ProviderAccessContextRef:
    operator = mode is ProviderAccessMode.OPERATOR_MANAGED
    return ProviderAccessContextRef(
        provider_key="youtube" if operator else "generic",
        profile_version="youtube-v2" if operator else "1",
        access_mode=mode,
        credential_version_id="version-1" if operator else None,
        egress_affinity_id="provider:youtube" if operator else "default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit="5d6b8c8",
    )
