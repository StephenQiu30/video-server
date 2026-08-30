from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

from app.application.provider_catalog import ProviderCatalogRepository
from app.application.providers import ProviderStatusView, provider_user_action
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
    ProviderSupportStatus,
)

_ACCESS_ERRORS = {"provider_auth_required", "provider_session_expired"}
_RATE_ERRORS = {"provider_rate_limited"}
_OPERATIONAL_DECISION_WINDOW = timedelta(hours=26)
_PERMANENT_ERRORS = {
    "provider_content_restricted",
    "provider_drm_protected",
    "provider_geo_restricted",
    "provider_link_unavailable",
    "provider_unsupported",
}


class ProviderCanaryReader(Protocol):
    async def list_recent(
        self,
        *,
        limit_per_provider_stage: int,
        scopes: Mapping[str, ProviderEvidenceScope],
    ) -> Mapping[str, tuple[ProviderCanaryResult, ...]]: ...


class ProviderRuntimeContextReader(Protocol):
    async def contexts_for_providers(
        self,
        requested: Mapping[str, ProviderAccessMode],
    ) -> Mapping[str, ProviderAccessContextRef]: ...


@dataclass(frozen=True, slots=True)
class ProviderEvidenceScope:
    """The one live runtime context allowed to affect public Provider status."""

    profile_version: str | None
    access_context: ProviderAccessContextRef

    def __post_init__(self) -> None:
        if (
            self.profile_version is not None
            and self.profile_version != self.access_context.profile_version
        ):
            raise ValueError("Provider evidence profile does not match live context")

    @property
    def access_mode(self) -> ProviderAccessMode:
        return self.access_context.access_mode

    @property
    def engine_commit(self) -> str:
        return self.access_context.engine_commit

    @property
    def context_generation_id(self) -> str:
        return self.access_context.generation_id


class ProviderStatusService:
    def __init__(
        self,
        reader: ProviderCanaryReader,
        baselines: tuple[ProviderStatusView, ...],
        *,
        now: Callable[[], datetime],
        context_reader: ProviderRuntimeContextReader,
        approved_keys: frozenset[str] = frozenset(),
        catalog: ProviderCatalogRepository | None = None,
    ) -> None:
        registered = {
            item.key
            for item in baselines
            if item.registered
            and item.status
            not in {
                ProviderSupportStatus.DISABLED,
                ProviderSupportStatus.UNSUPPORTED,
            }
        }
        if not approved_keys <= registered:
            raise ValueError("approved Provider key is not registered")
        self._reader = reader
        self._baselines = baselines
        self._now = now
        self._approved_keys = approved_keys
        self._catalog = catalog
        self._context_reader = context_reader

    async def list(self) -> tuple[ProviderStatusView, ...]:
        contexts = await _runtime_contexts(self._baselines, self._context_reader)
        recent = await self._reader.list_recent(
            limit_per_provider_stage=32,
            scopes=_evidence_scopes(
                self._baselines,
                contexts=contexts,
            ),
        )
        now = self._now()
        merged = tuple(
            _merge_status(
                view,
                recent.get(view.key, ()),
                now,
                explicitly_approved=view.key in self._approved_keys,
                context_generation_id=(
                    contexts[view.key].generation_id if view.key in contexts else None
                ),
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
                profile_version=None,
                registered=False,
                extractor_exists=False,
                capabilities=(),
                access_modes=(),
                status=ProviderSupportStatus.UNSUPPORTED,
                last_checked_at=None,
                last_check_succeeded=None,
                download_available=False,
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
    context_generation_id: str | None,
) -> ProviderStatusView:
    if baseline.status in {
        ProviderSupportStatus.DISABLED,
        ProviderSupportStatus.UNSUPPORTED,
    }:
        return baseline
    access_mode = _status_access_mode(baseline)
    if access_mode is None:
        return baseline
    if context_generation_id is None:
        return replace(
            baseline,
            status=ProviderSupportStatus.DEGRADED,
            download_available=False,
            user_action=provider_user_action(
                ProviderSupportStatus.DEGRADED,
                baseline.key,
                download_available=False,
                access_mode=access_mode,
            ),
        )
    results = tuple(
        item
        for item in results
        if item.access_mode is access_mode
        and item.context_generation_id == context_generation_id
        and (
            baseline.profile_version is None
            or item.profile_version == baseline.profile_version
        )
    )
    if not results:
        return baseline
    ordered = tuple(
        sorted(
            results,
            key=lambda item: (item.checked_at, item.target_id),
            reverse=True,
        )
    )
    decision_results = tuple(
        item
        for item in ordered
        if item.checked_at >= now - _OPERATIONAL_DECISION_WINDOW
    )
    latest = ordered[0]
    latest_decision = decision_results[0] if decision_results else None
    failures = tuple(
        item
        for item in decision_results[:5]
        if item.outcome is ProviderCanaryOutcome.FAILED
    )
    error = None if latest_decision is None else latest_decision.stable_error_code
    if error in _ACCESS_ERRORS:
        status = ProviderSupportStatus.ACCESS_REQUIRED
    elif error in _RATE_ERRORS:
        status = ProviderSupportStatus.RATE_LIMITED
    elif _blocked(decision_results):
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
    download_available = _download_available(ordered, now)
    return ProviderStatusView(
        key=baseline.key,
        display_name=baseline.display_name,
        profile_version=baseline.profile_version,
        registered=baseline.registered,
        extractor_exists=baseline.extractor_exists,
        capabilities=baseline.capabilities,
        access_modes=baseline.access_modes,
        status=status,
        last_checked_at=latest.checked_at,
        last_check_succeeded=(latest.outcome is ProviderCanaryOutcome.SUCCEEDED),
        download_available=download_available,
        last_media_verified_at=(
            _latest_success(ordered, ProviderCanaryStage.MEDIA)
            or baseline.last_media_verified_at
        ),
        last_verified_at=verified_at or baseline.last_verified_at,
        user_action=provider_user_action(
            status,
            baseline.key,
            download_available=download_available,
            access_mode=access_mode,
        ),
    )


def _evidence_scopes(
    baselines: tuple[ProviderStatusView, ...],
    *,
    contexts: Mapping[str, ProviderAccessContextRef],
) -> Mapping[str, ProviderEvidenceScope]:
    scopes: dict[str, ProviderEvidenceScope] = {}
    for baseline in baselines:
        if baseline.status in {
            ProviderSupportStatus.DISABLED,
            ProviderSupportStatus.UNSUPPORTED,
        }:
            continue
        access_mode = _status_access_mode(baseline)
        if access_mode is not None:
            context = contexts.get(baseline.key)
            if context is None:
                continue
            scopes[baseline.key] = ProviderEvidenceScope(
                profile_version=baseline.profile_version,
                access_context=context,
            )
    return scopes


async def _runtime_contexts(
    baselines: tuple[ProviderStatusView, ...],
    reader: ProviderRuntimeContextReader,
) -> Mapping[str, ProviderAccessContextRef]:
    requested = {
        baseline.key: access_mode
        for baseline in baselines
        if (access_mode := _status_access_mode(baseline)) is not None
    }
    try:
        resolved = await reader.contexts_for_providers(requested)
    except Exception:
        # Public status must never reuse stale evidence when the live runner
        # generation cannot be established.
        return {}
    profile_versions = {
        baseline.key: baseline.profile_version for baseline in baselines
    }
    return {
        key: context
        for key, context in resolved.items()
        if key in requested
        and context.provider_key == key
        and context.access_mode is requested[key]
        and (
            profile_versions[key] is None
            or context.profile_version == profile_versions[key]
        )
    }


def _status_access_mode(
    baseline: ProviderStatusView,
) -> ProviderAccessMode | None:
    access_modes = baseline.access_modes
    if (
        baseline.status is ProviderSupportStatus.ACCESS_REQUIRED
        and ProviderAccessMode.OPERATOR_MANAGED in access_modes
    ):
        return ProviderAccessMode.OPERATOR_MANAGED
    if ProviderAccessMode.ANONYMOUS in access_modes:
        return ProviderAccessMode.ANONYMOUS
    return access_modes[0] if access_modes else None


def _blocked(results: tuple[ProviderCanaryResult, ...]) -> bool:
    if len(results) < 3:
        return False
    errors = tuple(item.stable_error_code for item in results[:3])
    return errors[0] in _PERMANENT_ERRORS and len(set(errors)) == 1


def _verified(results: tuple[ProviderCanaryResult, ...], now: datetime) -> bool:
    metadata = tuple(
        item for item in results if item.stage is ProviderCanaryStage.METADATA
    )
    media = tuple(item for item in results if item.stage is ProviderCanaryStage.MEDIA)
    if not metadata or not media:
        return False
    remaining = tuple(
        sorted(
            (*metadata[1:], *media[1:]),
            key=lambda item: (item.checked_at, item.target_id),
            reverse=True,
        )
    )
    # Always reserve one slot for each operational stage. Real download evidence
    # is MEDIA-only and must not crowd a fresh METADATA probe out of this window.
    operational = (metadata[0], media[0], *remaining[:3])
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
    metadata_ok = metadata[0].checked_at >= metadata_cutoff
    media_ok = media[0].checked_at >= media_cutoff
    analysis_cutoff = now - timedelta(days=7)
    analysis_ok = any(
        item.outcome is ProviderCanaryOutcome.SUCCEEDED
        and item.stage is ProviderCanaryStage.ANALYSIS
        and item.checked_at >= analysis_cutoff
        for item in results
    )
    return metadata_ok and media_ok and analysis_ok


def _download_available(
    results: tuple[ProviderCanaryResult, ...], now: datetime
) -> bool:
    latest_media = next(
        (item for item in results if item.stage is ProviderCanaryStage.MEDIA),
        None,
    )
    return bool(
        latest_media is not None
        and latest_media.outcome is ProviderCanaryOutcome.SUCCEEDED
        and latest_media.checked_at >= now - timedelta(hours=26)
    )


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
