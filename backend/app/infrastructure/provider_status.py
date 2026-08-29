"""Configured Provider status snapshot without credentials or canary targets."""

from __future__ import annotations

from collections.abc import Set

from app.application.providers import ProviderStatusView, provider_user_action
from app.domain.providers import ProviderAccessMode, ProviderSupportStatus
from app.runner.provider_registry import ProviderProfile, current_provider_registry


def configured_provider_statuses(
    enabled_operator_keys: Set[str] = frozenset(),
) -> tuple[ProviderStatusView, ...]:
    configured = tuple(
        _configured_status(profile, enabled_operator_keys)
        for profile in current_provider_registry().profiles
    )
    non_runner = (
        ProviderStatusView(
            key="wechat_official_account_article",
            display_name="微信公众号文章",
            profile_version=None,
            registered=True,
            extractor_exists=False,
            capabilities=(),
            access_modes=(),
            status=ProviderSupportStatus.UNKNOWN,
            last_checked_at=None,
            last_check_succeeded=None,
            download_available=False,
            last_media_verified_at=None,
            last_verified_at=None,
            user_action="支持公开文章视频发现与显式选择；原生视频下载尚未通过发布验收。",
        ),
    )
    return configured + non_runner


current_provider_statuses = configured_provider_statuses


def _configured_status(
    profile: ProviderProfile,
    enabled_operator_keys: Set[str],
) -> ProviderStatusView:
    access_modes = (
        ()
        if profile.support_status is ProviderSupportStatus.DISABLED
        else _effective_access_modes(
            profile.key, profile.access_modes, enabled_operator_keys
        )
    )
    status = (
        profile.support_status
        if access_modes or profile.support_status is ProviderSupportStatus.DISABLED
        else ProviderSupportStatus.ACCESS_REQUIRED
    )
    return ProviderStatusView(
        key=profile.key,
        display_name=profile.display_name,
        profile_version=profile.version,
        registered=True,
        extractor_exists=True,
        capabilities=tuple(sorted(profile.capabilities, key=str)),
        access_modes=access_modes,
        status=status,
        last_checked_at=None,
        last_check_succeeded=None,
        download_available=False,
        last_media_verified_at=None,
        last_verified_at=None,
        user_action=provider_user_action(status, profile.key),
    )


def _effective_access_modes(
    provider_key: str,
    declared: tuple[ProviderAccessMode, ...],
    enabled_operator_keys: Set[str],
) -> tuple[ProviderAccessMode, ...]:
    return tuple(
        mode
        for mode in declared
        if mode is ProviderAccessMode.ANONYMOUS or provider_key in enabled_operator_keys
    )
