"""Mainstream social and video provider profiles."""

from app.domain.providers import ProviderCapability, ProviderSupportStatus
from app.runner.provider_factories import CHROME_IMPERSONATION, standard_provider
from app.runner.provider_normalizers import vimeo_url, wechat_channels_url
from app.runner.provider_registry import ProviderProfile

SOCIAL_PROVIDER_PROFILES: tuple[ProviderProfile, ...] = (
    standard_provider(
        "wechat_channels",
        "微信视频号",
        ("weixin.qq.com",),
        version="wechat-channels-public-v2",
        normalize_url=wechat_channels_url,
        capabilities=frozenset(
            {ProviderCapability.SINGLE_VIDEO, ProviderCapability.SHORT_VIDEO}
        ),
        status=ProviderSupportStatus.DEGRADED,
        command_args=CHROME_IMPERSONATION,
        client_profile_id="chrome-136-macos-15",
        canary_suite="wechat-channels-public-single-video",
    ),
    standard_provider(
        "vimeo",
        "Vimeo",
        ("vimeo.com", "www.vimeo.com", "player.vimeo.com"),
        normalize_url=vimeo_url,
        status=ProviderSupportStatus.VERIFIED,
        operator_cookie_domains=frozenset({"vimeo.com"}),
        command_args=("--check-formats",),
    ),
    standard_provider(
        "x",
        "X / Twitter",
        (
            "x.com",
            "www.x.com",
            "twitter.com",
            "www.twitter.com",
            "mobile.twitter.com",
        ),
        status=ProviderSupportStatus.VERIFIED,
        operator_cookie_domains=frozenset({"x.com", "twitter.com"}),
    ),
    standard_provider(
        "instagram",
        "Instagram",
        ("instagram.com", "www.instagram.com"),
        status=ProviderSupportStatus.VERIFIED,
        operator_cookie_domains=frozenset({"instagram.com"}),
    ),
    standard_provider(
        "facebook",
        "Facebook",
        (
            "facebook.com",
            "www.facebook.com",
            "web.facebook.com",
            "m.facebook.com",
            "fb.watch",
        ),
        version="facebook-public-reel-v1",
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.SHORT_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
            }
        ),
        status=ProviderSupportStatus.VERIFIED,
        operator_cookie_domains=frozenset({"facebook.com"}),
        command_args=CHROME_IMPERSONATION,
        client_profile_id="chrome-136-macos-15",
        canary_suite="facebook-public-reel-single-video",
    ),
    standard_provider(
        "twitch",
        "Twitch",
        ("twitch.tv", "www.twitch.tv", "clips.twitch.tv"),
        version="twitch-public-clip-v1",
        capabilities=frozenset(
            {ProviderCapability.SINGLE_VIDEO, ProviderCapability.CLIP_OR_VOD}
        ),
        status=ProviderSupportStatus.VERIFIED,
        canary_suite="twitch-public-clip",
    ),
    standard_provider(
        "reddit",
        "Reddit",
        ("reddit.com", "www.reddit.com", "old.reddit.com", "redd.it"),
        version="reddit-public-video-v1",
        capabilities=frozenset({ProviderCapability.SINGLE_VIDEO}),
        status=ProviderSupportStatus.ACCESS_REQUIRED,
        operator_cookie_domains=frozenset({"reddit.com"}),
        canary_suite="reddit-anonymous-operator-video",
    ),
)
