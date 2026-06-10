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


# --- Security: reject localhost, private, loopback, link-local, reserved addresses ---


def test_normalize_user_url_rejects_localhost() -> None:
    """本机地址 localhost 应被拒绝，返回 unsafe_url 错误码。"""
    for host in ["localhost", "localhost:8080"]:
        try:
            normalize_user_url(f"http://{host}/video")
        except AppError as exc:
            assert exc.code == "unsafe_url", f"host={host} code={exc.code}"
            assert exc.status_code == 422
        else:
            raise AssertionError(f"expected rejection for host={host}")


def test_normalize_user_url_rejects_private_ip() -> None:
    """内网地址 (10/172.16/192.168) 应被拒绝，返回 unsafe_url 错误码。"""
    for host in ["10.0.0.1", "172.16.0.1", "192.168.1.1", "192.168.1.1:3000"]:
        try:
            normalize_user_url(f"http://{host}/video")
        except AppError as exc:
            assert exc.code == "unsafe_url", f"host={host} code={exc.code}"
        else:
            raise AssertionError(f"expected rejection for host={host}")


def test_normalize_user_url_rejects_loopback_ip() -> None:
    """回环地址 127.x 应被拒绝，返回 unsafe_url 错误码。"""
    for host in ["127.0.0.1", "127.0.0.1:8080"]:
        try:
            normalize_user_url(f"http://{host}/video")
        except AppError as exc:
            assert exc.code == "unsafe_url", f"host={host} code={exc.code}"
        else:
            raise AssertionError(f"expected rejection for host={host}")


def test_normalize_user_url_rejects_ipv6_loopback() -> None:
    """IPv6 回环地址 ::1 应被拒绝，返回 unsafe_url 错误码。"""
    try:
        normalize_user_url("http://[::1]/video")
    except AppError as exc:
        assert exc.code == "unsafe_url"
    else:
        raise AssertionError("expected rejection for ::1")


def test_normalize_user_url_rejects_link_local_ip() -> None:
    """链路本地地址 169.254.x 应被拒绝，返回 unsafe_url 错误码。"""
    try:
        normalize_user_url("http://169.254.1.1/video")
    except AppError as exc:
        assert exc.code == "unsafe_url"
    else:
        raise AssertionError("expected rejection for link-local")


def test_normalize_user_url_rejects_reserved_ip() -> None:
    """保留地址应被拒绝（0.0.0.0、240.x），返回 unsafe_url 错误码。"""
    for host in ["0.0.0.0", "240.0.0.1"]:
        try:
            normalize_user_url(f"http://{host}/video")
        except AppError as exc:
            assert exc.code == "unsafe_url", f"host={host} code={exc.code}"
        else:
            raise AssertionError(f"expected rejection for host={host}")


def test_normalize_user_url_rejects_localhost_tld() -> None:
    """*.localhost 和 *.local 域名应被拒绝，返回 unsafe_url 错误码。"""
    for host in ["my.localhost", "device.local"]:
        try:
            normalize_user_url(f"http://{host}/video")
        except AppError as exc:
            assert exc.code == "unsafe_url", f"host={host} code={exc.code}"
        else:
            raise AssertionError(f"expected rejection for host={host}")


def test_normalize_user_url_rejects_multicast_ip() -> None:
    """组播地址应被拒绝，返回 unsafe_url 错误码。"""
    try:
        normalize_user_url("http://224.0.0.1/video")
    except AppError as exc:
        assert exc.code == "unsafe_url"
    else:
        raise AssertionError("expected rejection for multicast")


def test_normalize_user_url_unsafe_url_message_guides_user() -> None:
    """unsafe_url 错误消息应指导用户下一步。"""
    try:
        normalize_user_url("http://127.0.0.1/video")
    except AppError as exc:
        assert exc.code == "unsafe_url"
        assert "本机" in exc.message or "内网" in exc.message or "保留" in exc.message
    else:
        raise AssertionError("expected unsafe_url error")


def test_normalize_user_url_rejects_empty_string() -> None:
    """空字符串应被拒绝，返回 invalid_url 错误码。"""
    try:
        normalize_user_url("")
    except AppError as exc:
        assert exc.code == "invalid_url"
    else:
        raise AssertionError("expected invalid_url for empty string")


def test_normalize_user_url_rejects_whitespace_only() -> None:
    """纯空白字符串应被拒绝，返回 invalid_url 错误码。"""
    try:
        normalize_user_url("   ")
    except AppError as exc:
        assert exc.code == "invalid_url"
    else:
        raise AssertionError("expected invalid_url for whitespace")


def test_normalize_user_url_accepts_public_url() -> None:
    """公网域名应正常通过。"""
    assert normalize_user_url("https://bilibili.com/video/BV1xx411c7mD") == "https://bilibili.com/video/BV1xx411c7mD"
    assert normalize_user_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
