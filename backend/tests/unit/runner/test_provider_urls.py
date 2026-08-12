import pytest
from app.domain.providers import ProviderCapability, ProviderSupportStatus
from app.runner.errors import RunnerFailure
from app.runner.provider_registry import configure_provider_instances, provider_profile
from app.runner.provider_urls import (
    provider_command_args,
    provider_inspection_attempts,
    provider_inspection_retry_delay,
    provider_request_url,
)


def test_uses_public_vimeo_player_endpoint_for_canonical_video() -> None:
    assert (
        provider_request_url("https://vimeo.com/76979871?share=copy")
        == "https://player.vimeo.com/video/76979871"
    )
    assert (
        provider_request_url("https://www.vimeo.com/76979871/")
        == "https://player.vimeo.com/video/76979871"
    )


@pytest.mark.parametrize(
    "url",
    (
        "https://vimeo.com/76979871",
        "https://x.com/canghe/status/2087368911625052411",
        "https://www.instagram.com/reel/DbKfjdhTMAY/",
        "https://www.facebook.com/reel/1195289147628387",
        "https://clips.twitch.tv/FaintLightGullWholeWheat",
        "https://www.pinterest.com/pin/664281013778109217/",
        "https://weibo.com/7827771738/N4xlMvjhI",
        "https://v.youku.com/v_show/id_XOTUxMzg4NDMy.html",
        "https://v.qq.com/x/page/q326831cny0.html",
        "https://www.snapchat.com/spotlight/W7_EDlXWTBiXAEEniNoMPwAAYYWtidGhudGZpAX1TKn0JAX1TKnXJAAAAAA",
        "https://www.linkedin.com/posts/the-mathworks_2_what-is-mathworks-cloud-center-activity-7151241570371948544-4Gu7",
        "https://t.me/europa_press/613",
        "https://kick.com/spreen/clips/clip_01J8RGZRKHXHXXKJEHGRM932A5",
        "https://www.tumblr.com/maskofthedragon/626907179849564160/mona-talking-in-english",
    ),
)
def test_verified_provider_status(url: str) -> None:
    assert provider_profile(url).support_status is ProviderSupportStatus.VERIFIED


def test_preserves_unlisted_and_non_vimeo_urls() -> None:
    assert (
        provider_request_url("https://vimeo.com/76979871/private-hash")
        == "https://vimeo.com/76979871/private-hash"
    )


def test_remaining_provider_profiles_record_verified_access_boundaries() -> None:
    facebook = provider_profile("https://www.facebook.com/reel/1195289147628387")
    twitch = provider_profile("https://clips.twitch.tv/FaintLightGullWholeWheat")
    reddit = provider_profile("https://www.reddit.com/comments/124pp33")
    tiktok = provider_profile(
        "https://www.tiktok.com/@creator/video/6742501081818877190"
    )

    assert facebook.version == "facebook-public-reel-v1"
    assert facebook.client_profile_id == "chrome-136-macos-15"
    assert ProviderCapability.SHORT_VIDEO in facebook.capabilities
    assert twitch.version == "twitch-public-clip-v1"
    assert twitch.capabilities == frozenset(
        {
            ProviderCapability.SINGLE_VIDEO,
            ProviderCapability.CLIP_OR_VOD,
        }
    )
    assert reddit.support_status is ProviderSupportStatus.ACCESS_REQUIRED
    assert reddit.version == "reddit-public-video-v1"
    assert tiktok.support_status is ProviderSupportStatus.DEGRADED
    assert tiktok.version == "tiktok-web-v1"


def test_new_social_profiles_have_versioned_single_media_boundaries() -> None:
    expected = {
        "https://www.snapchat.com/spotlight/example_1": (
            "snapchat-spotlight-v1",
            "yt-dlp-default",
        ),
        "https://www.linkedin.com/posts/example-activity-1234567890-example": (
            "linkedin-public-post-v1",
            "yt-dlp-default",
        ),
        "https://t.me/example_channel/613": (
            "telegram-public-channel-post-v1",
            "yt-dlp-default",
        ),
        "https://kick.com/example/clips/clip_01ABCDEF": (
            "kick-public-clip-v1",
            "yt-dlp-default",
        ),
        "https://www.tumblr.com/example/1234567890/video": (
            "tumblr-public-video-post-v1",
            "chrome-136-macos-15",
        ),
    }

    assert {
        url: (provider_profile(url).version, provider_profile(url).client_profile_id)
        for url in expected
    } == expected


@pytest.mark.parametrize(
    "url",
    (
        "https://www.snapchat.com/add/example",
        "https://www.linkedin.com/company/example/",
        "https://t.me/example_channel",
        "https://kick.com/example",
        "https://kick.com/example/videos/12345678-abcd",
        "https://www.tumblr.com/example",
    ),
)
def test_new_social_profiles_reject_non_single_video_paths(url: str) -> None:
    with pytest.raises(RunnerFailure) as captured:
        provider_request_url(url)
    assert captured.value.code == "provider_unsupported"


def test_normalizes_kick_clip_query_to_the_clip_endpoint() -> None:
    assert (
        provider_request_url("https://kick.com/example?clip=clip_01ABCDEF")
        == "https://kick.com/example/clips/clip_01ABCDEF"
    )


def test_strips_linkedin_share_tracking_from_public_video_posts() -> None:
    assert provider_request_url(
        "https://www.linkedin.com/feed/update/urn:li:activity:7016901149999955968/"
        "?utm_source=share&utm_medium=member_desktop"
    ) == ("https://www.linkedin.com/feed/update/urn:li:activity:7016901149999955968/")


def test_normalizes_douyin_shared_video_urls() -> None:
    assert (
        provider_request_url(
            "https://www.douyin.com/jingxuan?modal_id=7647907920252949425"
        )
        == "https://www.douyin.com/video/7647907920252949425"
    )
    assert (
        provider_request_url("https://www.douyin.com/share/video/7647907920252949425")
        == "https://www.douyin.com/video/7647907920252949425"
    )
    assert provider_request_url("https://www.douyin.com/video/123") == (
        "https://www.douyin.com/video/123"
    )
    assert (
        provider_request_url("https://media.example.com/76979871")
        == "https://media.example.com/76979871"
    )


def test_targets_tiktok_request_impersonation_and_retries() -> None:
    url = "https://www.tiktok.com/@creator/video/123"

    assert provider_command_args(url) == (
        "--impersonate",
        "Chrome-136:Macos-15",
    )
    assert provider_inspection_attempts(url) == 8
    assert provider_inspection_retry_delay(url) == 0.5
    assert provider_command_args("https://vimeo.com/123") == ()
    assert provider_inspection_attempts("https://vimeo.com/123") == 2
    assert provider_inspection_retry_delay("https://vimeo.com/123") == 1


def test_targets_douyin_request_impersonation_and_retries() -> None:
    url = "https://www.douyin.com/video/123"

    assert provider_command_args(url) == (
        "--impersonate",
        "Chrome-136:Macos-15",
    )
    assert provider_inspection_attempts(url) == 8
    assert provider_inspection_retry_delay(url) == 0.5

    short_url = "https://v.douyin.com/example/"
    assert provider_command_args(short_url) == (
        "--impersonate",
        "Chrome-136:Macos-15",
    )
    assert provider_inspection_attempts(short_url) == 8


def test_targets_xiaohongshu_short_links_with_browser_impersonation() -> None:
    for url in (
        "https://xhslink.com/m/AbC123",
        "https://www.xiaohongshu.com/explore/abc123",
    ):
        assert provider_command_args(url) == (
            "--impersonate",
            "Chrome-136:Macos-15",
        )
        assert provider_inspection_attempts(url) == 8
        assert provider_inspection_retry_delay(url) == 0.5


def test_normalizes_kuaishou_public_videos_and_uses_android_impersonation() -> None:
    url = "https://www.kuaishou.com/short-video/3x888mrikrur4g2"

    assert provider_request_url(url) == (
        "https://v.m.chenzhongtech.com/fw/photo/3x888mrikrur4g2"
    )
    assert provider_command_args(url) == (
        "--impersonate",
        "Chrome-131:Android-14",
    )
    assert provider_inspection_attempts(url) == 4
    assert provider_inspection_retry_delay(url) == 0.5
    assert provider_request_url("https://v.kuaishou.com/8qIlZu") == (
        "https://v.kuaishou.com/8qIlZu"
    )


@pytest.mark.parametrize(
    "url",
    (
        "https://www.acfun.cn/v/ac35457073",
        "https://rutube.ru/video/0123456789abcdef0123456789abcdef",
        "https://m.vk.ru/clip123_456/",
        "https://geo.dailymotion.com/video/1",
        "https://www.nicovideo.jp/watch/sm1",
    ),
)
def test_removed_platforms_fail_closed_instead_of_using_generic(url: str) -> None:
    with pytest.raises(RunnerFailure) as captured:
        provider_profile(url)
    assert captured.value.code == "provider_unsupported"

    with pytest.raises(RunnerFailure) as captured:
        provider_request_url(url)
    assert captured.value.code == "provider_unsupported"


def test_registry_classifies_mainstream_platform_hosts() -> None:
    expected = {
        "youtube.com": "youtube",
        "b23.tv": "bilibili",
        "www.douyin.com": "douyin",
        "vm.tiktok.com": "tiktok",
        "xhslink.com": "xiaohongshu",
        "www.xiaohongshu.com": "xiaohongshu",
        "v.kuaishou.com": "kuaishou",
        "v.m.chenzhongtech.com": "kuaishou",
        "m.gifshow.com": "kuaishou",
        "player.vimeo.com": "vimeo",
        "x.com": "x",
        "www.instagram.com": "instagram",
        "fb.watch": "facebook",
        "web.facebook.com": "facebook",
        "clips.twitch.tv": "twitch",
        "redd.it": "reddit",
        "pin.it": "pinterest",
        "m.weibo.cn": "weibo",
        "v.youku.com": "youku",
        "v.qq.com": "qqvideo",
        "www.snapchat.com": "snapchat",
        "www.linkedin.com": "linkedin",
        "t.me": "telegram",
        "kick.com": "kick",
        "www.tumblr.com": "tumblr",
    }

    assert {
        hostname: provider_profile(f"https://{hostname}/video/1").key
        for hostname in expected
    } == expected


def test_unknown_hosts_use_the_safe_generic_strategy() -> None:
    profile = provider_profile("https://media.example.com/video/1")

    assert profile.key == "generic"
    assert profile.command_args == ()
    assert profile.inspection_attempts == 2


def test_peertube_requires_an_exact_approved_instance_and_video_path() -> None:
    configure_provider_instances(frozenset({"video.example.com"}))
    try:
        url = "https://video.example.com/w/AbCdEfGhIjKlMnOpQrStUv"
        profile = provider_profile(url)

        assert profile.key == "peertube"
        assert profile.version == "peertube-approved-instance-v1"
        assert provider_request_url(url) == url
        assert (
            provider_profile(
                "https://unapproved.example.com/w/AbCdEfGhIjKlMnOpQrStUv"
            ).key
            == "generic"
        )
        with pytest.raises(RunnerFailure) as captured:
            provider_request_url("https://video.example.com/videos/recently-added")
        assert captured.value.code == "provider_unsupported"
    finally:
        configure_provider_instances(frozenset())
