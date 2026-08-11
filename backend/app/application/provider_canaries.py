from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Protocol

from app.application.providers import ProviderStatusView
from app.domain.providers import (
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
    ProviderSupportStatus,
)

_ACCESS_ERRORS = {"provider_auth_required", "provider_session_expired"}
_RATE_ERRORS = {"provider_rate_limited"}
_PERMANENT_ERRORS = {
    "provider_content_restricted",
    "provider_drm_protected",
    "provider_geo_restricted",
    "provider_link_unavailable",
    "provider_unsupported",
}


class ProviderCanaryReader(Protocol):
    async def list_recent(
        self, *, limit_per_provider: int
    ) -> Mapping[str, tuple[ProviderCanaryResult, ...]]: ...


class ProviderStatusService:
    def __init__(
        self,
        reader: ProviderCanaryReader,
        baselines: tuple[ProviderStatusView, ...],
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._reader = reader
        self._baselines = baselines
        self._now = now

    async def list(self) -> tuple[ProviderStatusView, ...]:
        recent = await self._reader.list_recent(limit_per_provider=5)
        now = self._now()
        return tuple(
            _merge_status(view, recent.get(view.key, ()), now)
            for view in self._baselines
        )


def _merge_status(
    baseline: ProviderStatusView,
    results: tuple[ProviderCanaryResult, ...],
    now: datetime,
) -> ProviderStatusView:
    if not results or baseline.status is ProviderSupportStatus.UNSUPPORTED:
        return baseline
    ordered = tuple(sorted(results, key=lambda item: item.checked_at, reverse=True))
    latest = ordered[0]
    failures = tuple(
        item for item in ordered if item.outcome is ProviderCanaryOutcome.FAILED
    )
    error = latest.stable_error_code
    if error in _ACCESS_ERRORS:
        status = ProviderSupportStatus.ACCESS_REQUIRED
    elif error in _RATE_ERRORS:
        status = ProviderSupportStatus.RATE_LIMITED
    elif _blocked(ordered):
        status = ProviderSupportStatus.BLOCKED
    elif len(failures) >= 2:
        status = ProviderSupportStatus.DEGRADED
    # Unknown/access-required profiles need an explicit complete-video Agent E2E
    # approval before configuration can make them eligible for verified recovery.
    elif baseline.status is ProviderSupportStatus.VERIFIED and _verified(ordered, now):
        status = ProviderSupportStatus.VERIFIED
    else:
        status = baseline.status
    verified_at = _latest_media_success(ordered)
    return ProviderStatusView(
        key=baseline.key,
        display_name=baseline.display_name,
        registered=baseline.registered,
        extractor_exists=baseline.extractor_exists,
        capabilities=baseline.capabilities,
        access_modes=baseline.access_modes,
        status=status,
        last_verified_at=verified_at or baseline.last_verified_at,
        user_action=_user_action(status),
    )


def _blocked(results: tuple[ProviderCanaryResult, ...]) -> bool:
    if len(results) < 3:
        return False
    errors = tuple(item.stable_error_code for item in results[:3])
    return errors[0] in _PERMANENT_ERRORS and len(set(errors)) == 1


def _verified(results: tuple[ProviderCanaryResult, ...], now: datetime) -> bool:
    if len(results) < 5 or any(
        item.outcome is ProviderCanaryOutcome.FAILED for item in results[:2]
    ):
        return False
    successes = sum(item.outcome is ProviderCanaryOutcome.SUCCEEDED for item in results)
    if successes < 4:
        return False
    metadata_cutoff = now - timedelta(hours=6)
    media_cutoff = now - timedelta(hours=26)
    metadata_ok = any(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED
        and item.checked_at >= metadata_cutoff
        for item in results
    )
    media_ok = any(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED
        and item.stage is ProviderCanaryStage.MEDIA
        and item.checked_at >= media_cutoff
        for item in results
    )
    return metadata_ok and media_ok


def _latest_media_success(
    results: tuple[ProviderCanaryResult, ...],
) -> datetime | None:
    return next(
        (
            item.checked_at
            for item in results
            if item.stage is ProviderCanaryStage.MEDIA
            and item.outcome is ProviderCanaryOutcome.SUCCEEDED
        ),
        None,
    )


def _user_action(status: ProviderSupportStatus) -> str | None:
    if status is ProviderSupportStatus.ACCESS_REQUIRED:
        return "该平台需要部署已批准的受控会话；未启用时请稍后重试。"
    if status in {
        ProviderSupportStatus.DEGRADED,
        ProviderSupportStatus.RATE_LIMITED,
        ProviderSupportStatus.BLOCKED,
    }:
        return "平台当前不稳定，请稍后重试。"
    if status is ProviderSupportStatus.UNKNOWN:
        return "该平台尚未完成当前版本的真实下载验证。"
    if status is ProviderSupportStatus.DISABLED:
        return "该平台能力已由运维关闭。"
    return None
