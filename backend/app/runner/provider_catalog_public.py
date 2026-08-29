"""Public single-media provider profiles."""

from app.domain.providers import ProviderCapability, ProviderSupportStatus
from app.runner.provider_factories import CHROME_IMPERSONATION, standard_provider
from app.runner.provider_normalizers import (
    hongguo_url,
    kick_url,
    linkedin_url,
    snapchat_url,
    telegram_url,
    tumblr_url,
)
from app.runner.provider_registry import ProviderProfile

SINGLE_VIDEO = frozenset({ProviderCapability.SINGLE_VIDEO})

PUBLIC_PROVIDER_PROFILES: tuple[ProviderProfile, ...] = (
    standard_provider(
        "pinterest",
        "Pinterest",
        ("pinterest.com", "www.pinterest.com", "pin.it"),
        version="pinterest-public-video-pin-v1",
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="pinterest-public-video-pin",
    ),
    standard_provider(
        "weibo",
        "微博",
        ("weibo.com", "www.weibo.com", "weibo.cn", "m.weibo.cn"),
        version="weibo-public-video-v1",
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="weibo-public-single-video",
    ),
    standard_provider(
        "youku",
        "优酷",
        ("youku.com", "www.youku.com", "v.youku.com"),
        version="youku-public-video-v1",
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="youku-public-single-video",
    ),
    standard_provider(
        "qqvideo",
        "腾讯视频",
        ("v.qq.com",),
        version="qqvideo-public-video-v1",
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.DISABLED,
        canary_suite="qqvideo-public-single-video",
    ),
    standard_provider(
        "snapchat",
        "Snapchat Spotlight",
        ("snapchat.com", "www.snapchat.com"),
        version="snapchat-spotlight-v1",
        normalize_url=snapchat_url,
        capabilities=frozenset(
            {ProviderCapability.SINGLE_VIDEO, ProviderCapability.SHORT_VIDEO}
        ),
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="snapchat-public-spotlight",
    ),
    standard_provider(
        "linkedin",
        "LinkedIn",
        ("linkedin.com", "www.linkedin.com"),
        version="linkedin-public-post-v1",
        normalize_url=linkedin_url,
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="linkedin-public-single-video-post",
    ),
    standard_provider(
        "telegram",
        "Telegram",
        ("t.me",),
        version="telegram-public-channel-post-v1",
        normalize_url=telegram_url,
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="telegram-public-channel-single-video",
    ),
    standard_provider(
        "kick",
        "Kick",
        ("kick.com", "www.kick.com"),
        version="kick-public-clip-v1",
        normalize_url=kick_url,
        capabilities=frozenset(
            {ProviderCapability.SINGLE_VIDEO, ProviderCapability.CLIP_OR_VOD}
        ),
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="kick-public-clip",
    ),
    standard_provider(
        "tumblr",
        "Tumblr",
        ("tumblr.com", "www.tumblr.com"),
        version="tumblr-public-video-post-v1",
        normalize_url=tumblr_url,
        host_suffixes=frozenset({"tumblr.com"}),
        capabilities=SINGLE_VIDEO,
        status=ProviderSupportStatus.VERIFIED,
        command_args=CHROME_IMPERSONATION,
        client_profile_id="chrome-136-macos-15",
        canary_suite="tumblr-public-single-video-post",
        inspection_attempts=4,
        inspection_retry_delay=4,
    ),
    ProviderProfile(
        key="hongguo_web",
        display_name="红果短剧官方分享",
        hosts=frozenset({"novelquickapp.com", "hongguoduanju.com"}),
        version="hongguo-official-share-v1",
        normalize_url=hongguo_url,
        capabilities=SINGLE_VIDEO,
        support_status=ProviderSupportStatus.UNKNOWN,
        canary_suite="hongguo-official-share-single-video",
    ),
)
