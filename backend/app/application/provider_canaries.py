from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Protocol

from app.application.provider_catalog import ProviderCatalogRepository
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
        approved_keys: frozenset[str] = frozenset(),
        catalog: ProviderCatalogRepository | None = None,
    ) -> None:
        registered = {
            item.key
            for item in baselines
            if item.registered and item.status is not ProviderSupportStatus.UNSUPPORTED
        }
        if not approved_keys <= registered:
            raise ValueError("approved Provider key is not registered")
        self._reader = reader
        self._baselines = baselines
        self._now = now
        self._approved_keys = approved_keys
        self._catalog = catalog

    async def list(self) -> tuple[ProviderStatusView, ...]:
        recent = await self._reader.list_recent(limit_per_provider=32)
        now = self._now()
        merged = tuple(
            _merge_status(
                view,
                recent.get(view.key, ()),
                now,
                explicitly_approved=view.key in self._approved_keys,
            )
            for view in self._baselines
        )
        if self._catalog is None:
            return merged
        entries = await self._catalog.list_entries(visible_only=True)
        by_key = {item.key: item for item in merged}
        return tuple(
            replace(by_key[entry.key], display_name=entry.display_name)
            if entry.key in by_key
            else ProviderStatusView(
                key=entry.key,
                display_name=entry.display_name,
                registered=False,
                extractor_exists=False,
                capabilities=(),
                access_modes=(),
                status=ProviderSupportStatus.UNSUPPORTED,
                last_media_verified_at=None,
                last_verified_at=None,
                user_action="当前安全执行器不支持该平台。",
            )
            for entry in entries
        )


def _merge_status(
    baseline: ProviderStatusView,
    results: tuple[ProviderCanaryResult, ...],
    now: datetime,
    *,
    explicitly_approved: bool,
) -> ProviderStatusView:
    if baseline.status is ProviderSupportStatus.UNSUPPORTED:
        return baseline
    if not results:
        if baseline.status is not ProviderSupportStatus.VERIFIED:
            return baseline
        return replace(
            baseline,
            status=ProviderSupportStatus.UNKNOWN,
            last_verified_at=None,
            user_action=_user_action(ProviderSupportStatus.UNKNOWN, baseline.key),
        )
    ordered = tuple(sorted(results, key=lambda item: item.checked_at, reverse=True))
    latest = ordered[0]
    failures = tuple(
        item for item in ordered[:5] if item.outcome is ProviderCanaryOutcome.FAILED
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
    elif (
        baseline.status is ProviderSupportStatus.VERIFIED or explicitly_approved
    ) and _verified(ordered, now):
        status = ProviderSupportStatus.VERIFIED
    else:
        status = baseline.status
    verified_at = _latest_analysis_success(ordered)
    return ProviderStatusView(
        key=baseline.key,
        display_name=baseline.display_name,
        registered=baseline.registered,
        extractor_exists=baseline.extractor_exists,
        capabilities=baseline.capabilities,
        access_modes=baseline.access_modes,
        status=status,
        last_media_verified_at=(
            _latest_success(ordered, ProviderCanaryStage.MEDIA)
            or baseline.last_media_verified_at
        ),
        last_verified_at=verified_at or baseline.last_verified_at,
        user_action=_user_action(status, baseline.key),
    )


def _blocked(results: tuple[ProviderCanaryResult, ...]) -> bool:
    if len(results) < 3:
        return False
    errors = tuple(item.stable_error_code for item in results[:3])
    return errors[0] in _PERMANENT_ERRORS and len(set(errors)) == 1


def _verified(results: tuple[ProviderCanaryResult, ...], now: datetime) -> bool:
    operational = tuple(
        item for item in results if item.stage is not ProviderCanaryStage.ANALYSIS
    )[:5]
    if len(operational) < 5 or any(
        item.outcome is ProviderCanaryOutcome.FAILED for item in operational[:2]
    ):
        return False
    successes = sum(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED for item in operational
    )
    if successes < 4:
        return False
    metadata_cutoff = now - timedelta(hours=6)
    media_cutoff = now - timedelta(hours=26)
    metadata_ok = any(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED
        and item.stage is ProviderCanaryStage.METADATA
        and item.checked_at >= metadata_cutoff
        for item in operational
    )
    media_ok = any(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED
        and item.stage is ProviderCanaryStage.MEDIA
        and item.checked_at >= media_cutoff
        for item in operational
    )
    analysis_cutoff = now - timedelta(days=7)
    analysis_ok = any(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED
        and item.stage is ProviderCanaryStage.ANALYSIS
        and item.checked_at >= analysis_cutoff
        for item in results
    )
    return metadata_ok and media_ok and analysis_ok


def _latest_analysis_success(
    results: tuple[ProviderCanaryResult, ...],
) -> datetime | None:
    return _latest_success(results, ProviderCanaryStage.ANALYSIS)


def _latest_success(
    results: tuple[ProviderCanaryResult, ...], stage: ProviderCanaryStage
) -> datetime | None:
    return next(
        (
            item.checked_at
            for item in results
            if item.stage is stage and item.outcome is ProviderCanaryOutcome.SUCCEEDED
        ),
        None,
    )


def _user_action(
    status: ProviderSupportStatus, provider_key: str | None = None
) -> str | None:
    if provider_key == "hongguo_web" and status is ProviderSupportStatus.UNKNOWN:
        return (
            "已接入红果官方分享链接当前单集；"
            "不支持 App 受保护媒体、全集抓取或批量下载。"
        )
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
