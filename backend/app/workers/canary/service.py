from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Protocol
from uuid import uuid4

from app.application.downloads import (
    MediaInspectionAuthRequired,
    MediaInspectionContentRestricted,
    MediaInspectionDrmProtected,
    MediaInspectionFailure,
    MediaInspectionGeoRestricted,
    MediaInspectionLinkUnavailable,
    MediaInspectionMediaUnsupported,
    MediaInspectionRateLimited,
    MediaInspectionSessionExpired,
    MediaInspectionTemporarilyUnavailable,
    MediaInspectionTimeout,
    MediaInspectionUnsupported,
    MediaInspectionVerificationFailed,
    RunnerInspection,
)
from app.domain.downloads import DownloadPlan
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
from app.runner.provider_registry import provider_profile
from app.runner.version import YTDLP_ENGINE_COMMIT
from app.workers.canary.targets import ProviderCanaryTarget

_INSPECTION_ERRORS: tuple[tuple[type[Exception], str], ...] = (
    (MediaInspectionAuthRequired, "provider_auth_required"),
    (MediaInspectionSessionExpired, "provider_session_expired"),
    (MediaInspectionVerificationFailed, "provider_verification_failed"),
    (MediaInspectionRateLimited, "provider_rate_limited"),
    (MediaInspectionGeoRestricted, "provider_geo_restricted"),
    (MediaInspectionContentRestricted, "provider_content_restricted"),
    (MediaInspectionDrmProtected, "provider_drm_protected"),
    (MediaInspectionTemporarilyUnavailable, "provider_temporarily_unavailable"),
    (MediaInspectionLinkUnavailable, "provider_link_unavailable"),
    (MediaInspectionMediaUnsupported, "provider_media_unsupported"),
    (MediaInspectionUnsupported, "provider_unsupported"),
    (MediaInspectionTimeout, "inspection_timeout"),
    (MediaInspectionFailure, "inspection_failed"),
)
_RUNNER_ERRORS = {
    "download_timeout",
    "client_context_mismatch",
    "extractor_regression",
    "format_unavailable",
    "provider_rate_limited",
    "provider_link_unavailable",
    "provider_temporarily_unavailable",
    "runner_unavailable",
}
_RUNNER_ERROR_ALIASES = {
    "egress_challenged": "provider_verification_failed",
    "pot_required": "provider_verification_failed",
    "pot_rejected": "provider_verification_failed",
    "drm_protected": "provider_drm_protected",
    "content_private": "provider_content_restricted",
    "content_not_entitled": "provider_content_restricted",
    "content_entitlement_unknown": "provider_content_restricted",
    "credential_required": "provider_auth_required",
    "provider_session_not_allowed": "provider_auth_required",
    "credential_expired": "provider_session_expired",
    "credential_rejected": "provider_session_expired",
    "credential_revoked": "provider_session_expired",
    "provider_geo_restricted": "provider_geo_restricted",
    "provider_media_unsupported": "provider_media_unsupported",
    "provider_unsupported": "provider_unsupported",
    "invalid_artifact_path": "media_validation_failed",
    "media_validation_failed": "media_validation_failed",
    "workspace_limit_exceeded": "output_limit_exceeded",
}
_FORMAT_DRIFT_ATTEMPTS = 3


class CanaryRepository(Protocol):
    async def save(self, result: ProviderCanaryResult) -> None: ...

    async def latest_checked_at(
        self,
        target_id: str,
        profile_version: str,
        stage: ProviderCanaryStage,
        access_mode: ProviderAccessMode,
    ) -> datetime | None: ...


class CanaryRunner(Protocol):
    async def inspect(
        self,
        url: str,
        *,
        access_mode: ProviderAccessMode,
    ) -> RunnerInspection: ...

    async def download(
        self,
        task_id: str,
        url: str,
        plan: DownloadPlan,
        *,
        expected_provider_media_id: str,
        expected_extractor_key: str,
        access_context: ProviderAccessContextRef,
    ) -> RunnerArtifact: ...


class WorkspaceCleaner(Protocol):
    async def cleanup(self, task_id: str, workspace: Path | None) -> None: ...


class ProviderCanaryService:
    def __init__(
        self,
        repository: CanaryRepository,
        runner: CanaryRunner,
        cleaner: WorkspaceCleaner,
        *,
        now: Callable[[], datetime],
        timer: Callable[[], float] = monotonic,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._cleaner = cleaner
        self._now = now
        self._timer = timer

    async def execute(self, target: ProviderCanaryTarget) -> ProviderCanaryResult:
        started = self._timer()
        task_id = f"canary_{uuid4().hex}"
        workspace = None
        profile = provider_profile(target.safe_url())
        context = None
        error: str | None = None
        try:
            inspection = await self._runner.inspect(
                target.safe_url(),
                access_mode=target.access_mode,
            )
            inspected_context = inspection.access_context
            if (
                inspected_context.provider_key != target.provider_key
                or inspected_context.profile_version != profile.version
                or inspected_context.access_mode is not target.access_mode
            ):
                raise MediaRunnerClientError("client_context_mismatch", 502)
            context = inspected_context
            if target.stage is ProviderCanaryStage.MEDIA:
                artifact, inspection = await self._download_media(
                    target,
                    task_id,
                    inspection,
                )
                context = inspection.access_context
                workspace = artifact.workspace
        except Exception as exc:
            error = _stable_error(exc)
        finally:
            if target.stage is ProviderCanaryStage.MEDIA:
                await self._cleaner.cleanup(task_id, workspace)
        result = ProviderCanaryResult(
            target_id=target.target_id,
            provider_key=target.provider_key,
            profile_version=context.profile_version if context else profile.version,
            stage=target.stage,
            access_mode=target.access_mode,
            outcome=(
                ProviderCanaryOutcome.SUCCEEDED
                if error is None
                else ProviderCanaryOutcome.FAILED
            ),
            stable_error_code=error,
            checked_at=self._now(),
            duration_ms=max(0, round((self._timer() - started) * 1000)),
            engine_commit=context.engine_commit if context else YTDLP_ENGINE_COMMIT,
            egress_affinity_id=(
                context.egress_affinity_id if context else profile.egress_pool
            ),
            client_profile_id=(
                context.client_profile_id if context else profile.client_profile_id
            ),
        )
        await self._repository.save(result)
        return result

    async def _download_media(
        self,
        target: ProviderCanaryTarget,
        task_id: str,
        inspection: RunnerInspection,
    ) -> tuple[RunnerArtifact, RunnerInspection]:
        """Retry only a rendition rotation, never a platform/access failure."""
        for attempt in range(_FORMAT_DRIFT_ATTEMPTS):
            if not inspection.formats:
                raise MediaRunnerClientError("format_unavailable", 409)
            # The browser selects the first advertised format by default. Keep
            # the media canary on the same path so it detects regressions in
            # the format most users actually download.
            canary_format = inspection.formats[0]
            try:
                artifact = await self._runner.download(
                    task_id,
                    target.safe_url(),
                    canary_format.plan,
                    expected_provider_media_id=inspection.provider_media_id,
                    expected_extractor_key=inspection.extractor_key,
                    access_context=inspection.access_context,
                )
                return artifact, inspection
            except MediaRunnerClientError as exc:
                if (
                    exc.code != "format_unavailable"
                    or attempt == _FORMAT_DRIFT_ATTEMPTS - 1
                ):
                    raise
                inspection = await self._runner.inspect(
                    target.safe_url(),
                    access_mode=target.access_mode,
                )
                context = inspection.access_context
                profile = provider_profile(target.safe_url())
                if (
                    context.provider_key != target.provider_key
                    or context.profile_version != profile.version
                    or context.access_mode is not target.access_mode
                ):
                    raise MediaRunnerClientError(
                        "client_context_mismatch", 502
                    ) from exc
        raise AssertionError("unreachable")


def _stable_error(exc: Exception) -> str:
    if isinstance(exc, MediaRunnerClientError):
        if exc.code in _RUNNER_ERRORS:
            return exc.code
        return _RUNNER_ERROR_ALIASES.get(exc.code, "runner_failed")
    return next(
        (
            code
            for error_type, code in _INSPECTION_ERRORS
            if isinstance(exc, error_type)
        ),
        "canary_internal_error",
    )
