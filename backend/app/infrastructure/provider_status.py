"""Configured Provider status snapshot without credentials or canary targets."""

from __future__ import annotations

from app.application.providers import ProviderStatusView
from app.domain.providers import ProviderSupportStatus
from app.runner.provider_registry import current_provider_registry


def configured_provider_statuses() -> tuple[ProviderStatusView, ...]:
    configured = tuple(
        ProviderStatusView(
            key=profile.key,
            display_name=profile.display_name,
            registered=True,
            extractor_exists=True,
            capabilities=tuple(sorted(profile.capabilities, key=str)),
            access_modes=profile.access_modes,
            status=profile.support_status,
            last_media_verified_at=None,
            last_verified_at=None,
            user_action=_user_action(profile.support_status, profile.key),
        )
        for profile in current_provider_registry().profiles
    )
    unsupported = (
        ProviderStatusView(
            key="wechat_channels",
            display_name="微信视频号",
            registered=False,
            extractor_exists=False,
            capabilities=(),
            access_modes=(),
            status=ProviderSupportStatus.UNSUPPORTED,
            last_media_verified_at=None,
            last_verified_at=None,
            user_action="当前安全执行器不支持该平台。",
        ),
    )
    return configured + unsupported


current_provider_statuses = configured_provider_statuses


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
