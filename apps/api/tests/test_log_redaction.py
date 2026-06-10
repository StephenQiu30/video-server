"""Tests for logging redaction: URL sanitization and sensitive keyword handling."""

import logging

from app.core.logging import JSONFormatter


def _format_message(formatter: JSONFormatter, message: str) -> str:
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0, msg=message, args=(), exc_info=None
    )
    return formatter.format(record)


def test_redacts_sensitive_query_params_in_url() -> None:
    """URL 中的敏感查询参数应被脱敏，但 URL 本身保留。"""
    formatter = JSONFormatter()
    output = _format_message(formatter, "Parsing https://example.com/video?id=1&token=secret123&sig=abc")
    assert "secret123" not in output
    assert "https://example.com/video" in output


def test_does_not_redact_normal_message() -> None:
    """不含敏感信息的正常日志消息不应被脱敏。"""
    formatter = JSONFormatter()
    output = _format_message(formatter, "User uploaded video successfully")
    assert "User uploaded video successfully" in output


def test_redacts_password_field_value() -> None:
    """日志中 password=xxx 的值应被脱敏。"""
    formatter = JSONFormatter()
    output = _format_message(formatter, "Login attempt password=hunter2 for user@test.com")
    assert "hunter2" not in output


def test_redacts_authorization_header_value() -> None:
    """日志中 authorization=xxx 的值应被脱敏。"""
    formatter = JSONFormatter()
    output = _format_message(formatter, "Request with authorization=Bearer_abc123xyz")
    assert "Bearer_abc123xyz" not in output


def test_preserves_non_sensitive_key_value() -> None:
    """不含敏感关键字的 key=value 对不应被脱敏。"""
    formatter = JSONFormatter()
    output = _format_message(formatter, "Processing request_id=abc-123 status=ok")
    assert "request_id=abc-123" in output
    assert "status=ok" in output


def test_redacts_url_in_error_context() -> None:
    """错误上下文中的 URL 敏感参数应被脱敏。"""
    formatter = JSONFormatter()
    output = _format_message(
        formatter,
        "Parse failed for https://example.com/video?id=1&token=t123&access_token=at456",
    )
    assert "t123" not in output
    assert "at456" not in output
