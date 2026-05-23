from app.services.platforms import find_platform_profile


def test_platform_profile_matches_mainland_short_video_hosts() -> None:
    cases = [
        ("https://www.douyin.com/video/123", "douyin", "抖音", "domestic_short_video"),
        ("https://www.kuaishou.com/short-video/abc", "kuaishou", "快手", "domestic_short_video"),
        ("https://www.xiaohongshu.com/explore/abc", "xiaohongshu", "小红书", "domestic_short_video"),
        ("https://www.ixigua.com/123", "ixigua", "西瓜视频", "domestic_short_video"),
        ("https://m.weibo.cn/status/123", "weibo", "微博", "domestic_short_video"),
    ]

    for url, platform_id, display_name, category in cases:
        profile = find_platform_profile(url)

        assert profile is not None
        assert profile.id == platform_id
        assert profile.display_name == display_name
        assert profile.category == category


def test_platform_profile_matches_bilibili_short_hosts() -> None:
    for url in [
        "https://b23.tv/abc",
        "https://m.bilibili.com/video/BV1xx411c7mD",
        "https://www.bilibili.com/video/BV1xx411c7mD",
    ]:
        profile = find_platform_profile(url)

        assert profile is not None
        assert profile.id == "bilibili"
        assert profile.display_name == "B 站"
        assert profile.category == "long_video"


def test_platform_profile_marks_known_public_fallback_hosts() -> None:
    cases = [
        ("https://youtu.be/abc", "youtube"),
        ("https://www.youtube.com/watch?v=abc", "youtube"),
        ("https://www.tiktok.com/@u/video/123", "tiktok"),
    ]

    for url, platform_id in cases:
        profile = find_platform_profile(url)

        assert profile is not None
        assert profile.id == platform_id
        assert profile.supports_public_parse is True
