from app.services.platforms import find_platform_profile, validate_supported_download_url


def test_platform_profile_matches_mainland_short_video_hosts() -> None:
    cases = [
        ("https://www.douyin.com/video/123", "douyin", "抖音", "cn-short-video"),
        ("https://www.kuaishou.com/short-video/abc", "kuaishou", "快手", "cn-short-video"),
        ("https://www.xiaohongshu.com/explore/abc", "xiaohongshu", "小红书", "cn-short-video"),
        ("https://www.ixigua.com/123", "ixigua", "西瓜视频", "cn-short-video"),
        ("https://m.weibo.cn/status/123", "weibo", "微博", "cn-short-video"),
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
        assert profile.category == "cn-video"


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


# --- STE-54: Extended platform profile assertions ---


def test_all_platforms_have_profile_fields() -> None:
    """Every supported platform returns id, display_name, and category."""
    cases = [
        ("https://www.douyin.com/video/123", "douyin", "抖音", "cn-short-video"),
        ("https://www.kuaishou.com/short-video/abc", "kuaishou", "快手", "cn-short-video"),
        ("https://www.xiaohongshu.com/explore/abc", "xiaohongshu", "小红书", "cn-short-video"),
        ("https://www.ixigua.com/123", "ixigua", "西瓜视频", "cn-short-video"),
        ("https://m.weibo.cn/status/123", "weibo", "微博", "cn-short-video"),
        ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili", "B 站", "cn-video"),
        ("https://www.youtube.com/watch?v=abc", "youtube", "YouTube", "overseas-video"),
        ("https://www.tiktok.com/@u/video/123", "tiktok", "TikTok", "overseas-short-video"),
        ("https://vimeo.com/123456", "vimeo", "Vimeo", "overseas-video"),
        ("https://www.dailymotion.com/video/abc", "dailymotion", "Dailymotion", "overseas-video"),
        ("https://x.com/user/status/123", "x", "X", "social-platform"),
        ("https://www.instagram.com/reel/abc", "instagram", "Instagram", "social-platform"),
    ]

    for url, expected_id, expected_name, expected_category in cases:
        profile = find_platform_profile(url)

        assert profile is not None, f"no profile for {url}"
        assert profile.id == expected_id
        assert profile.display_name == expected_name
        assert profile.category == expected_category


def test_high_risk_platforms_have_compliance_note() -> None:
    """All formally supported platforms carry a compliance_note."""
    high_risk_urls = [
        "https://www.douyin.com/video/123",
        "https://www.kuaishou.com/short-video/abc",
        "https://www.xiaohongshu.com/explore/abc",
        "https://www.ixigua.com/123",
        "https://m.weibo.cn/status/123",
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://x.com/user/status/123",
        "https://www.instagram.com/reel/abc",
    ]

    for url in high_risk_urls:
        profile = find_platform_profile(url)

        assert profile is not None, f"no profile for {url}"
        assert profile.compliance_note is not None, f"{profile.id} missing compliance_note"
        assert len(profile.compliance_note) > 0


def test_platform_profile_matches_x_hosts() -> None:
    """X (formerly Twitter) URLs are recognized with social-platform category."""
    for url in [
        "https://x.com/user/status/123",
        "https://twitter.com/user/status/123",
        "https://www.x.com/user/status/123",
    ]:
        profile = find_platform_profile(url)

        assert profile is not None, f"no profile for {url}"
        assert profile.id == "x"
        assert profile.display_name == "X"
        assert profile.category == "social-platform"
        assert profile.compliance_note is not None


def test_platform_profile_matches_instagram_hosts() -> None:
    """Instagram URLs are recognized with social-platform category."""
    for url in [
        "https://www.instagram.com/reel/abc",
        "https://www.instagram.com/p/abc123",
        "https://instagram.com/stories/user/123",
    ]:
        profile = find_platform_profile(url)

        assert profile is not None, f"no profile for {url}"
        assert profile.id == "instagram"
        assert profile.display_name == "Instagram"
        assert profile.category == "social-platform"
        assert profile.compliance_note is not None


def test_unknown_public_host_returns_none() -> None:
    """Unknown public hosts are not rejected — they return None for yt-dlp fallback."""
    unknown_urls = [
        "https://example.com/video/123",
        "https://some-random-site.org/watch?v=abc",
    ]

    for url in unknown_urls:
        profile = find_platform_profile(url)
        assert profile is None, f"unexpected profile match for {url}"

        # validate_supported_download_url should also return None (not raise)
        result = validate_supported_download_url(url)
        assert result is None
