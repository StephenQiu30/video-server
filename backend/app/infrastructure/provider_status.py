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
            profile_version=profile.version,
            registered=True,
            extractor_exists=True,
            capabilities=tuple(sorted(profile.capabilities, key=str)),
            access_modes=profile.access_modes,
            status=profile.support_status,
            last_checked_at=None,
            last_check_succeeded=None,
            download_available=False,
            last_media_verified_at=None,
            last_verified_at=None,
            user_action=_user_action(profile.support_status, profile.key),
        )
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


def _user_action(
    status: ProviderSupportStatus, provider_key: str | None = None
) -> str | None:
    if provider_key == "hongguo_web":
        return (
            "已接入红果官方分享链接当前单集；"
            "不支持 App 受保护媒体、全集抓取或批量下载。"
        )
    if (
        provider_key == "xiaohongshu"
        and status is ProviderSupportStatus.DEGRADED
    ):
        return (
            "当前出口受到小红书官方风控；失效笔记会单独提示，"
            "请使用新的公开分享链接后稍后重试。"
        )
    if provider_key == "wechat_channels":
        return (
            "仅支持分享页直接公开非加密媒体的单视频；"
            "平台未公开媒体时请上传自己拥有或已获授权的文件。"
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
