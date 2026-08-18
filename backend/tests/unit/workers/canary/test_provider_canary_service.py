from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.application.downloads import (
    MediaInspectionAuthRequired,
    RunnerFormat,
    RunnerInspection,
)
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.media_runner_models import (
    MediaRunnerClientError,
    RunnerArtifact,
)
from app.workers.canary.service import ProviderCanaryService
from app.workers.canary.targets import ProviderCanaryTarget
from tests.unit.runner.helpers import download_request

NOW = datetime(2026, 8, 11, 5, tzinfo=UTC)
URL = "https://vimeo.com/76979871"


class Repository:
    def __init__(self) -> None:
        self.results: list[ProviderCanaryResult] = []

    async def save(self, result: ProviderCanaryResult) -> None:
        self.results.append(result)

    async def latest_checked_at(
        self, target_id: str, stage: ProviderCanaryStage
    ) -> datetime | None:
        return None


class Cleaner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path | None]] = []

    async def cleanup(self, task_id: str, workspace: Path | None) -> None:
        self.calls.append((task_id, workspace))


class Runner:
    def __init__(
        self,
        workspace: Path,
        *,
        fail: bool = False,
        format_drifts: int = 0,
    ) -> None:
        self.workspace = workspace
        self.fail = fail
        self.format_drifts = format_drifts
        self.downloaded = False
        self.inspections = 0
        self.download_calls = 0

    async def inspect(self, url: str) -> RunnerInspection:
        assert url == URL
        self.inspections += 1
        if self.fail:
            raise MediaInspectionAuthRequired
        request = download_request()
        return RunnerInspection(
            extractor_key="Vimeo",
            provider_media_id="76979871",
            title="Authorized canary",
            duration_seconds=30,
            formats=(RunnerFormat("1080p", request.plan.to_domain()),),
            access_context=ProviderAccessContextRef(
                provider_key="vimeo",
                profile_version="1",
                access_mode=ProviderAccessMode.ANONYMOUS,
                credential_version_id=None,
                egress_affinity_id="default",
                client_profile_id="yt-dlp-default",
                attestation_provider_version=None,
                engine_commit="5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc",
            ),
        )

    async def download(self, *args: object, **kwargs: object) -> RunnerArtifact:
        self.download_calls += 1
        if self.download_calls <= self.format_drifts:
            raise MediaRunnerClientError("format_unavailable", 409)
        self.downloaded = True
        return RunnerArtifact(
            task_id=str(args[0]),
            workspace=self.workspace,
            artifact=self.workspace / "video.mp4",
            size_bytes=1024,
            sha256="a" * 64,
            duration_seconds=30,
            container="mp4",
            video_streams=1,
            audio_streams=1,
        )


def target(stage: ProviderCanaryStage) -> ProviderCanaryTarget:
    return ProviderCanaryTarget(
        target_id="vimeo-owned-1",
        provider_key="vimeo",
        stage=stage,
        url=URL,
    )


@pytest.mark.asyncio
async def test_full_canary_downloads_and_cleans_verified_media(tmp_path: Path) -> None:
    repository, cleaner, runner = Repository(), Cleaner(), Runner(tmp_path)
    ticks = iter((1.0, 1.25))
    service = ProviderCanaryService(
        repository, runner, cleaner, now=lambda: NOW, timer=lambda: next(ticks)
    )

    result = await service.execute(target(ProviderCanaryStage.MEDIA))

    assert result.outcome is ProviderCanaryOutcome.SUCCEEDED
    assert result.duration_ms == 250
    assert runner.downloaded is True
    assert repository.results == [result]
    assert cleaner.calls[0][1] == tmp_path


@pytest.mark.asyncio
async def test_media_canary_reinspects_bounded_format_drift(tmp_path: Path) -> None:
    repository, cleaner = Repository(), Cleaner()
    runner = Runner(tmp_path, format_drifts=2)
    ticks = iter((1.0, 1.5))
    service = ProviderCanaryService(
        repository, runner, cleaner, now=lambda: NOW, timer=lambda: next(ticks)
    )

    result = await service.execute(target(ProviderCanaryStage.MEDIA))

    assert result.outcome is ProviderCanaryOutcome.SUCCEEDED
    assert runner.inspections == 3
    assert runner.download_calls == 3


@pytest.mark.asyncio
async def test_media_canary_translates_runner_drm_failure(tmp_path: Path) -> None:
    class DrmRunner(Runner):
        async def download(self, *args: object, **kwargs: object) -> RunnerArtifact:
            raise MediaRunnerClientError("drm_protected", 422)

    repository, cleaner = Repository(), Cleaner()
    ticks = iter((1.0, 1.1))
    service = ProviderCanaryService(
        repository,
        DrmRunner(tmp_path),
        cleaner,
        now=lambda: NOW,
        timer=lambda: next(ticks),
    )

    result = await service.execute(target(ProviderCanaryStage.MEDIA))

    assert result.outcome is ProviderCanaryOutcome.FAILED
    assert result.stable_error_code == "provider_drm_protected"


@pytest.mark.asyncio
async def test_media_canary_translates_runner_challenge_failure(tmp_path: Path) -> None:
    class ChallengeRunner(Runner):
        async def download(self, *args: object, **kwargs: object) -> RunnerArtifact:
            raise MediaRunnerClientError("egress_challenged", 422)

    repository, cleaner = Repository(), Cleaner()
    ticks = iter((1.0, 1.1))
    service = ProviderCanaryService(
        repository,
        ChallengeRunner(tmp_path),
        cleaner,
        now=lambda: NOW,
        timer=lambda: next(ticks),
    )

    result = await service.execute(target(ProviderCanaryStage.MEDIA))

    assert result.outcome is ProviderCanaryOutcome.FAILED
    assert result.stable_error_code == "provider_verification_failed"


@pytest.mark.asyncio
async def test_metadata_failure_is_persisted_as_stable_access_error(
    tmp_path: Path,
) -> None:
    repository, cleaner = Repository(), Cleaner()
    ticks = iter((1.0, 1.1))
    service = ProviderCanaryService(
        repository,
        Runner(tmp_path, fail=True),
        cleaner,
        now=lambda: NOW,
        timer=lambda: next(ticks),
    )

    result = await service.execute(target(ProviderCanaryStage.METADATA))

    assert result.outcome is ProviderCanaryOutcome.FAILED
    assert result.stable_error_code == "provider_auth_required"
    assert cleaner.calls == []
