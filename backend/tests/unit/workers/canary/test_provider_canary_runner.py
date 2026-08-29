from __future__ import annotations

from pathlib import Path

import pytest
from app.application.downloads import MediaInspectionAuthRequired, RunnerInspection
from app.domain.providers import ProviderAccessContextRef, ProviderAccessMode
from app.infrastructure.media_runner_models import RunnerArtifact
from app.workers.canary.runner import ProviderCanaryRunner

URL = "https://www.youtube.com/watch?v=owned"


class FakeClient:
    def __init__(self, access_mode: ProviderAccessMode) -> None:
        self.access_context = context(access_mode)
        self.error: Exception | None = None
        self.inspected: list[str] = []
        self.closed = False

    async def inspect(self, url: str) -> RunnerInspection:
        self.inspected.append(url)
        if self.error is not None:
            raise self.error
        return RunnerInspection(
            extractor_key="Youtube",
            provider_media_id="owned",
            title="Owned",
            duration_seconds=30,
            formats=(),
            access_context=self.access_context,
        )

    async def context(self, _url: str) -> ProviderAccessContextRef:
        return self.access_context

    async def download(self, task_id: str, *_args, **_kwargs) -> RunnerArtifact:
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

    async def status(self, _task_id: str) -> None:
        raise AssertionError("not used")

    async def cancel(self, _task_id: str) -> None:
        raise AssertionError("not used")

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_anonymous_failure_and_operator_success_remain_separate() -> None:
    anonymous = FakeClient(ProviderAccessMode.ANONYMOUS)
    anonymous.error = MediaInspectionAuthRequired()
    operator = FakeClient(ProviderAccessMode.OPERATOR_MANAGED)
    runner = ProviderCanaryRunner(anonymous, {"youtube": operator})  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionAuthRequired) as captured:
        await runner.inspect(URL, access_mode=ProviderAccessMode.ANONYMOUS)
    operator_result = await runner.inspect(
        URL,
        access_mode=ProviderAccessMode.OPERATOR_MANAGED,
    )

    assert captured.value.access_mode is ProviderAccessMode.ANONYMOUS
    assert anonymous.inspected == [URL]
    assert operator.inspected == [URL]
    assert (
        operator_result.access_context.access_mode
        is ProviderAccessMode.OPERATOR_MANAGED
    )


@pytest.mark.asyncio
async def test_missing_operator_is_attributed_to_operator_route() -> None:
    anonymous = FakeClient(ProviderAccessMode.ANONYMOUS)
    runner = ProviderCanaryRunner(anonymous)  # type: ignore[arg-type]

    with pytest.raises(MediaInspectionAuthRequired) as captured:
        await runner.inspect(URL, access_mode=ProviderAccessMode.OPERATOR_MANAGED)

    assert captured.value.access_mode is ProviderAccessMode.OPERATOR_MANAGED
    assert anonymous.inspected == []


def context(access_mode: ProviderAccessMode) -> ProviderAccessContextRef:
    operator = access_mode is ProviderAccessMode.OPERATOR_MANAGED
    return ProviderAccessContextRef(
        provider_key="youtube",
        profile_version="youtube-v4",
        access_mode=access_mode,
        credential_version_id="version-1" if operator else None,
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit="5d6b8c8",
    )
