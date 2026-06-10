import json
import logging

from app.core.logging import JSONFormatter
from app.utils.sanitize import redact_url, safe_filename


def test_redact_url_sensitive_query() -> None:
    url = redact_url("https://example.com/video?id=1&token=secret&signature=abc")
    assert "token=%2A%2A%2A" in url
    assert "signature=%2A%2A%2A" in url
    assert "secret" not in url


def test_redact_url_preserves_non_sensitive_params() -> None:
    """非敏感参数应保留原值。"""
    url = redact_url("https://example.com/video?id=1&page=2&lang=zh")
    assert "id=1" in url
    assert "page=2" in url
    assert "lang=zh" in url


def test_redact_url_all_sensitive_keys() -> None:
    """所有敏感 key 都应被脱敏。"""
    url = redact_url("https://example.com?a=1&token=t&signature=s&auth=a&cookie=c&key=k&access_token=at&session=sid")
    for key in ["token", "signature", "auth", "cookie", "key", "access_token", "session"]:
        assert f"{key}=%2A%2A%2A" in url, f"key={key} not redacted"
    assert "a=1" in url


def test_redact_url_no_query_params() -> None:
    """无 query 参数的 URL 应原样返回。"""
    url = redact_url("https://example.com/video")
    assert url == "https://example.com/video"


def test_redact_url_empty_string() -> None:
    """空字符串应原样返回。"""
    assert redact_url("") == ""


def test_safe_filename_removes_path_separators() -> None:
    assert safe_filename("../a/b:c.mp4") == "_a_b_c.mp4"


def test_json_formatter_redacts_sensitive_messages() -> None:
    """JSONFormatter 应脱敏包含敏感关键词的日志消息。"""
    formatter = JSONFormatter()
    for keyword in ["token", "cookie", "password", "authorization", "secret", "key"]:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=f"user provided {keyword}=abc123", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "[REDACTED]", f"keyword={keyword} not redacted"


def test_json_formatter_preserves_normal_messages() -> None:
    """JSONFormatter 应保留不含敏感关键词的普通消息。"""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="processing video https://example.com/watch?v=abc", args=(), exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["message"] == "processing video https://example.com/watch?v=abc"


def test_redact_url_preserves_fragment() -> None:
    """URL fragment 应保留。"""
    url = redact_url("https://example.com/video?id=1&t=120#section")
    assert "#section" in url
    assert "id=1" in url


def test_redact_url_case_insensitive_keys() -> None:
    """敏感 key 大小写不敏感。"""
    url = redact_url("https://example.com?TOKEN=secret&Token=value&token=abc")
    assert "TOKEN=%2A%2A%2A" in url
    assert "Token=%2A%2A%2A" in url
    assert "token=%2A%2A%2A" in url


def test_json_formatter_includes_timestamp_and_level() -> None:
    """JSONFormatter 输出应包含 timestamp 和 level 字段。"""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=0,
        msg="test message", args=(), exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert "timestamp" in data
    assert data["level"] == "WARNING"
    assert data["logger"] == "test"
