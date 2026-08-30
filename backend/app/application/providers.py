"""Public, non-secret Provider capability views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.providers import (
    ProviderAccessMode,
    ProviderCapability,
    ProviderSupportStatus,
)

YOUKU_PUBLIC_ONLY_ACTION = (
    "仅支持无需登录即可访问的公开、非 DRM 单视频；"
    "VIP、付费或试看内容请在优酷官方客户端播放。"
)
QQVIDEO_PLAYBACK_ONLY_ACTION = (
    "支持识别腾讯视频单视频链接并引导官方播放；"
    "消费端私有接口、VIP、付费及 DRM 内容不提供下载。"
    "自有媒资请通过腾讯云 VOD 官方导出或上传明文文件。"
)


@dataclass(frozen=True, slots=True)
class ProviderStatusView:
    key: str
    display_name: str
    profile_version: str | None
    registered: bool
    extractor_exists: bool
    capabilities: tuple[ProviderCapability, ...]
    access_modes: tuple[ProviderAccessMode, ...]
    status: ProviderSupportStatus
    last_checked_at: datetime | None
    last_check_succeeded: bool | None
    download_available: bool
    last_media_verified_at: datetime | None
    last_verified_at: datetime | None
    user_action: str | None

    @property
    def download_supported(self) -> bool:
        downloadable = {
            ProviderCapability.SINGLE_VIDEO,
            ProviderCapability.SHORT_VIDEO,
            ProviderCapability.CLIP_OR_VOD,
        }
        return (
            self.registered
            and self.extractor_exists
            and self.status
            not in {
                ProviderSupportStatus.DISABLED,
                ProviderSupportStatus.UNSUPPORTED,
            }
            and bool(downloadable.intersection(self.capabilities))
        )


def provider_user_action(
    status: ProviderSupportStatus,
    provider_key: str | None = None,
    *,
    download_available: bool = False,
    access_mode: ProviderAccessMode = ProviderAccessMode.ANONYMOUS,
) -> str | None:
    """Return the single public recovery message for one Provider state."""
    sample = (
        "公开样本" if access_mode is ProviderAccessMode.ANONYMOUS else "受控线路样本"
    )
    if provider_key == "youku":
        return YOUKU_PUBLIC_ONLY_ACTION
    if provider_key == "qqvideo":
        return QQVIDEO_PLAYBACK_ONLY_ACTION
    if status is ProviderSupportStatus.ACCESS_REQUIRED and download_available:
        return "真实下载已完成验证；当前链接仍可能因平台授权或验证要求失败。"
    if provider_key == "wechat_channels":
        return (
            "仅支持分享页直接公开非加密媒体的单视频；"
            "平台未公开媒体时请上传自己拥有或已获授权的文件。"
        )
    if provider_key == "hongguo_web":
        return (
            "已接入红果官方分享链接当前单集；"
            "不支持 App 受保护媒体、全集抓取或批量下载。"
        )
    if provider_key == "xiaohongshu" and status is ProviderSupportStatus.DEGRADED:
        return (
            "当前出口受到小红书官方风控；失效笔记会单独提示，"
            "请使用新的公开分享链接后稍后重试。"
        )
    if status is ProviderSupportStatus.ACCESS_REQUIRED:
        return (
            "该平台当前要求额外授权或验证；请稍后重试，或上传你拥有或已获授权的文件。"
        )
    if status in {
        ProviderSupportStatus.DEGRADED,
        ProviderSupportStatus.RATE_LIMITED,
        ProviderSupportStatus.BLOCKED,
    }:
        return "平台当前不稳定，请稍后重试。"
    if status is ProviderSupportStatus.UNKNOWN:
        if download_available:
            return f"{sample}已完成真实下载验证；完整视频分析链路仍待验证。"
        return "该平台尚未完成当前版本的真实下载验证。"
    if status is ProviderSupportStatus.DISABLED:
        return "当前未开放此平台下载。"
    return None
