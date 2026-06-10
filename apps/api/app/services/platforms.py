from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlparse

from app.core.errors import AppError


DEFAULT_COMPLIANCE_NOTE = "仅支持公开可访问内容；不支持 DRM、会员、付费或需登录内容。"
DOMESTIC_SHORT_VIDEO_COMPLIANCE_NOTE = "仅支持公开视频链接；平台风控、私密作品、登录态内容和付费内容不会绕过。"
BILIBILI_COMPLIANCE_NOTE = "仅支持公开视频；番剧、会员、付费、版权受限或需登录内容不会绕过。"


@dataclass(frozen=True)
class PlatformProfile:
    id: str
    display_name: str
    category: str
    hosts: tuple[str, ...]
    requires_public_access: bool = True
    supports_public_parse: bool = True
    compliance_note: str | None = DEFAULT_COMPLIANCE_NOTE

    def matches_host(self, host: str) -> bool:
        normalized = host.lower().strip(".")
        return any(normalized == item or normalized.endswith(f".{item}") for item in self.hosts)


PLATFORM_PROFILES: tuple[PlatformProfile, ...] = (
    PlatformProfile(
        id="bilibili",
        display_name="B 站",
        category="cn-video",
        hosts=("bilibili.com", "b23.tv"),
        compliance_note=BILIBILI_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="douyin",
        display_name="抖音",
        category="cn-short-video",
        hosts=("douyin.com", "iesdouyin.com"),
        compliance_note=DOMESTIC_SHORT_VIDEO_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="kuaishou",
        display_name="快手",
        category="cn-short-video",
        hosts=("kuaishou.com",),
        compliance_note=DOMESTIC_SHORT_VIDEO_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="xiaohongshu",
        display_name="小红书",
        category="cn-short-video",
        hosts=("xiaohongshu.com", "xhslink.com"),
        compliance_note=DOMESTIC_SHORT_VIDEO_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="ixigua",
        display_name="西瓜视频",
        category="cn-short-video",
        hosts=("ixigua.com",),
        compliance_note=DOMESTIC_SHORT_VIDEO_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="weibo",
        display_name="微博",
        category="cn-short-video",
        hosts=("weibo.com", "weibo.cn"),
        compliance_note=DOMESTIC_SHORT_VIDEO_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="tiktok",
        display_name="TikTok",
        category="overseas-short-video",
        hosts=("tiktok.com",),
    ),
    PlatformProfile(
        id="x",
        display_name="X",
        category="social-platform",
        hosts=("x.com", "twitter.com"),
        compliance_note=DEFAULT_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="instagram",
        display_name="Instagram",
        category="social-platform",
        hosts=("instagram.com",),
        compliance_note=DEFAULT_COMPLIANCE_NOTE,
    ),
    PlatformProfile(
        id="youtube",
        display_name="YouTube",
        category="overseas-video",
        hosts=("youtube.com", "youtu.be", "youtube-nocookie.com"),
    ),
    PlatformProfile(
        id="vimeo",
        display_name="Vimeo",
        category="overseas-video",
        hosts=("vimeo.com",),
    ),
    PlatformProfile(
        id="dailymotion",
        display_name="Dailymotion",
        category="overseas-video",
        hosts=("dailymotion.com", "dai.ly"),
    ),
)


def find_platform_profile(url: str) -> PlatformProfile | None:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return None
    return next((profile for profile in PLATFORM_PROFILES if profile.matches_host(host)), None)


def validate_supported_download_url(url: str) -> PlatformProfile | None:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        raise AppError("invalid_url", "请输入有效的视频链接", 422)

    profile = find_platform_profile(url)
    if profile:
        return profile

    if _is_blocked_host(host):
        raise AppError("unsupported_platform", "该链接暂不支持解析，请确认是否为公开视频链接", 422)

    # Keep yt-dlp's broad public-site fallback for unknown but valid public hosts.
    return None


def _is_blocked_host(host: str) -> bool:
    if host in {"localhost"} or host.endswith((".localhost", ".local", ".invalid")):
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return any(
        [
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        ]
    )
