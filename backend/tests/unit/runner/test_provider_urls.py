import pytest
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


def test_preserves_unlisted_and_non_vimeo_urls() -> None:
    assert (
        provider_request_url("https://vimeo.com/76979871/private-hash")
        == "https://vimeo.com/76979871/private-hash"
    )


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


def test_acfun_admits_only_public_single_video_paths() -> None:
    url = "https://www.acfun.cn/v/ac35457073?part=1"

    assert provider_request_url(url) == url
    try:
        provider_request_url("https://www.acfun.cn/bangumi/aa123")
    except RunnerFailure as exc:
        assert exc.code == "provider_unsupported"
    else:
        raise AssertionError("non-UGC AcFun path was accepted")


def test_rutube_admits_only_public_single_video_paths() -> None:
    video_id = "0123456789abcdef0123456789abcdef"
    for url in (
        f"https://rutube.ru/video/{video_id}/",
        f"https://rutube.ru/play/embed/{video_id}",
        "https://rutube.ru/video/embed/12345",
    ):
        assert provider_request_url(url) == url

    for url in (
        f"https://rutube.ru/video/private/{video_id}",
        f"https://rutube.ru/video/{video_id}?from=channel",
        "https://rutube.ru/channel/123/videos/",
    ):
        with pytest.raises(RunnerFailure) as captured:
            provider_request_url(url)
        assert captured.value.code == "provider_unsupported"


def test_vk_admits_only_direct_public_video_and_clip_paths() -> None:
    for url in (
        "https://vk.com/video-123_456",
        "https://m.vk.ru/clip123_456/",
        "https://vkvideo.ru/video1_2",
    ):
        assert provider_request_url(url) == url

    for url in (
        "https://vk.com/feed?z=video-123_456",
        "https://vk.com/video-123_456?list=abc",
        "https://vk.com/video_ext.php?oid=-123&id=456",
    ):
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
        "www.acfun.cn": "acfun",
        "rutube.ru": "rutube",
        "vk.com": "vk",
        "m.vk.ru": "vk",
        "vkvideo.ru": "vk",
        "player.vimeo.com": "vimeo",
        "x.com": "x",
        "www.instagram.com": "instagram",
        "fb.watch": "facebook",
        "clips.twitch.tv": "twitch",
        "redd.it": "reddit",
        "pin.it": "pinterest",
        "m.weibo.cn": "weibo",
        "v.youku.com": "youku",
        "v.qq.com": "qqvideo",
        "dai.ly": "dailymotion",
        "nico.ms": "niconico",
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


def test_acfun_has_a_versioned_unknown_public_profile() -> None:
    profile = provider_profile("https://www.acfun.cn/v/ac35457073")

    assert profile.key == "acfun"
    assert profile.version == "acfun-public-v1"
    assert profile.canary_suite == "acfun-public-single-video"
    assert profile.support_status.value == "unknown"


@pytest.mark.parametrize(
    ("url", "key", "version", "suite"),
    (
        (
            "https://rutube.ru/video/0123456789abcdef0123456789abcdef",
            "rutube",
            "rutube-public-v1",
            "rutube-public-single-video",
        ),
        (
            "https://vk.com/clip-123_456",
            "vk",
            "vk-public-v1",
            "vk-public-video-or-clip",
        ),
    ),
)
def test_incremental_profiles_are_versioned_and_unverified(
    url: str, key: str, version: str, suite: str
) -> None:
    profile = provider_profile(url)

    assert profile.key == key
    assert profile.version == version
    assert profile.canary_suite == suite
    assert profile.support_status.value == "unknown"


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
