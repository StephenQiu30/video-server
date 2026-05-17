from app.core.errors import AppError
from app.utils.url import normalize_user_url


def test_normalize_user_url_trims_and_adds_https_scheme() -> None:
    assert normalize_user_url(" bilibili.com/video/BV1xx411c7mD ") == "https://bilibili.com/video/BV1xx411c7mD"


def test_normalize_user_url_keeps_existing_https_scheme() -> None:
    assert normalize_user_url("https://example.com/video") == "https://example.com/video"


def test_normalize_user_url_rejects_non_http_scheme() -> None:
    try:
        normalize_user_url("ftp://example.com/video")
    except AppError as exc:
        assert exc.code == "invalid_url"
        assert exc.status_code == 422
    else:
        raise AssertionError("expected invalid URL")


def test_normalize_user_url_rejects_plain_text() -> None:
    try:
        normalize_user_url("not a url")
    except AppError as exc:
        assert exc.code == "invalid_url"
        assert "有效的视频链接" in exc.message
    else:
        raise AssertionError("expected invalid URL")


def test_normalize_user_url_extracts_from_share_text() -> None:
    # Douyin share text format
    douyin_text = "7.40 复制打开抖音，看看【小猫咪的作品】... https://v.douyin.com/iJxxqxx/ 完整复制此消息"
    assert normalize_user_url(douyin_text) == "https://v.douyin.com/iJxxqxx/"

    # Kuaishou share text format
    kuaishou_text = "快手【超级搞笑视频】 https://v.kuaishou.com/f/xxxxx 点击链接查看！"
    assert normalize_user_url(kuaishou_text) == "https://v.kuaishou.com/f/xxxxx"

    # Bilibili share text format
    bilibili_text = "【B站热门视频】 【小猫咪的作品】 🚀 https://bilibili.com/video/BV1xx411c7mD 哔哩哔哩"
    assert normalize_user_url(bilibili_text) == "https://bilibili.com/video/BV1xx411c7mD"
