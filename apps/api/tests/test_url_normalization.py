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
