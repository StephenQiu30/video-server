"""Built-in provider strategies backed by yt-dlp extractors."""

from __future__ import annotations

import re
from urllib.parse import SplitResult, parse_qs

from app.domain.providers import (
    ProviderAccessMode,
    ProviderCapability,
    ProviderSupportStatus,
)
from app.runner.provider_registry import ProviderProfile, UrlNormalizer, _identity

_VIMEO_ID = re.compile(r"/([0-9]+)/?$")
_DOUYIN_VIDEO = re.compile(r"/video/(?P<id>[0-9]+)/?$")
_DOUYIN_SHARE = re.compile(r"/share/video/(?P<id>[0-9]+)/?$")
_KUAISHOU_VIDEO = re.compile(r"/short-video/(?P<id>[A-Za-z0-9]+)/?$")
_DIGITS = re.compile(r"[0-9]+$")
_CHROME_IMPERSONATION = ("--impersonate", "Chrome-136:Macos-15")
_ANDROID_IMPERSONATION = ("--impersonate", "Chrome-131:Android-14")


def _vimeo_url(url: str, parsed: SplitResult) -> str:
    match = _VIMEO_ID.fullmatch(parsed.path)
    return url if match is None else f"https://player.vimeo.com/video/{match.group(1)}"


def _douyin_url(url: str, parsed: SplitResult) -> str:
    match = _DOUYIN_VIDEO.fullmatch(parsed.path) or _DOUYIN_SHARE.fullmatch(parsed.path)
    if match is not None:
        return f"https://www.douyin.com/video/{match.group('id')}"
    modal_id = parse_qs(parsed.query).get("modal_id", [])
    if len(modal_id) == 1 and _DIGITS.fullmatch(modal_id[0]):
        return f"https://www.douyin.com/video/{modal_id[0]}"
    return url


def _kuaishou_url(url: str, parsed: SplitResult) -> str:
    match = _KUAISHOU_VIDEO.fullmatch(parsed.path)
    if match is None:
        return url
    return f"https://v.m.chenzhongtech.com/fw/photo/{match.group('id')}"


def _standard(
    key: str,
    display_name: str,
    hosts: tuple[str, ...],
    *,
    normalize_url: UrlNormalizer = _identity,
    capabilities: frozenset[ProviderCapability] | None = None,
    status: ProviderSupportStatus = ProviderSupportStatus.UNKNOWN,
) -> ProviderProfile:
    return ProviderProfile(
        key,
        display_name,
        frozenset(hosts),
        capabilities=capabilities
        or frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
            }
        ),
        support_status=status,
        normalize_url=normalize_url,
    )


def _challenged(
    key: str,
    display_name: str,
    hosts: tuple[str, ...],
    *,
    normalize_url: UrlNormalizer = _identity,
    status: ProviderSupportStatus = ProviderSupportStatus.UNKNOWN,
) -> ProviderProfile:
    return ProviderProfile(
        key,
        display_name,
        frozenset(hosts),
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.SHORT_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
            }
        ),
        support_status=status,
        command_args=_CHROME_IMPERSONATION,
        inspection_attempts=8,
        inspection_retry_delay=0.5,
        normalize_url=normalize_url,
    )


DEFAULT_PROVIDER_PROFILES: tuple[ProviderProfile, ...] = (
    ProviderProfile(
        key="youtube",
        display_name="YouTube",
        hosts=frozenset(
            {
                "youtube.com",
                "www.youtube.com",
                "m.youtube.com",
                "music.youtube.com",
                "youtu.be",
                "youtube-nocookie.com",
                "www.youtube-nocookie.com",
            }
        ),
        version="youtube-v2",
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.SHORT_VIDEO,
                ProviderCapability.AUDIO_VIDEO_SPLIT,
                ProviderCapability.SUBTITLES,
            }
        ),
        access_modes=(
            ProviderAccessMode.ANONYMOUS,
            ProviderAccessMode.OPERATOR_MANAGED,
        ),
        cookie_domain_allowlist=frozenset({"youtube.com", "youtube-nocookie.com"}),
        attestation_policy="bgutil-mweb-gvs-optional",
        egress_pool="youtube-sticky",
        credential_concurrency=1,
        support_status=ProviderSupportStatus.ACCESS_REQUIRED,
        canary_suite="youtube-anonymous-operator-pot",
    ),
    _standard(
        "bilibili",
        "哔哩哔哩",
        ("bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"),
        status=ProviderSupportStatus.VERIFIED,
    ),
    _challenged(
        "douyin",
        "抖音",
        (
            "douyin.com",
            "www.douyin.com",
            "m.douyin.com",
            "v.douyin.com",
            "iesdouyin.com",
            "www.iesdouyin.com",
        ),
        normalize_url=_douyin_url,
        status=ProviderSupportStatus.VERIFIED,
    ),
    _challenged(
        "tiktok",
        "TikTok",
        (
            "tiktok.com",
            "www.tiktok.com",
            "m.tiktok.com",
            "vm.tiktok.com",
            "vt.tiktok.com",
        ),
    ),
    _challenged(
        "xiaohongshu",
        "小红书",
        (
            "xiaohongshu.com",
            "www.xiaohongshu.com",
            "xhslink.com",
            "www.xhslink.com",
        ),
        status=ProviderSupportStatus.VERIFIED,
    ),
    ProviderProfile(
        key="kuaishou",
        display_name="快手",
        hosts=frozenset(
            {
                "kuaishou.com",
                "www.kuaishou.com",
                "m.kuaishou.com",
                "v.kuaishou.com",
                "kuaishou.cn",
                "www.kuaishou.cn",
                "c.kuaishou.com",
                "v.m.chenzhongtech.com",
                "m.gifshow.com",
            }
        ),
        version="kuaishou-public-v1",
        capabilities=frozenset(
            {
                ProviderCapability.SINGLE_VIDEO,
                ProviderCapability.SHORT_VIDEO,
            }
        ),
        client_profile_id="chrome-131-android-14",
        support_status=ProviderSupportStatus.VERIFIED,
        canary_suite="kuaishou-public-share-page",
        command_args=_ANDROID_IMPERSONATION,
        inspection_attempts=4,
        inspection_retry_delay=0.5,
        normalize_url=_kuaishou_url,
    ),
    _standard(
        "vimeo",
        "Vimeo",
        ("vimeo.com", "www.vimeo.com", "player.vimeo.com"),
        normalize_url=_vimeo_url,
    ),
    _standard(
        "x",
        "X / Twitter",
        ("x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"),
    ),
    _standard("instagram", "Instagram", ("instagram.com", "www.instagram.com")),
    _standard(
        "facebook",
        "Facebook",
        ("facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"),
    ),
    _standard("twitch", "Twitch", ("twitch.tv", "www.twitch.tv", "clips.twitch.tv")),
    _standard(
        "reddit",
        "Reddit",
        ("reddit.com", "www.reddit.com", "old.reddit.com", "redd.it"),
    ),
    _standard(
        "pinterest", "Pinterest", ("pinterest.com", "www.pinterest.com", "pin.it")
    ),
    _standard(
        "weibo", "微博", ("weibo.com", "www.weibo.com", "weibo.cn", "m.weibo.cn")
    ),
    _standard("youku", "优酷", ("youku.com", "www.youku.com", "v.youku.com")),
    _standard("qqvideo", "腾讯视频", ("v.qq.com",)),
    _standard(
        "dailymotion",
        "Dailymotion",
        ("dailymotion.com", "www.dailymotion.com", "dai.ly"),
    ),
    _standard(
        "niconico", "ニコニコ動画", ("nicovideo.jp", "www.nicovideo.jp", "nico.ms")
    ),
)
