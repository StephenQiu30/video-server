from app.services.download_adapter import YtDlpAdapter


def test_classifies_login_required_as_platform_restricted() -> None:
    error = YtDlpAdapter().map_parse_error(RuntimeError("Login required to access this video"))

    assert error.code == "platform_restricted"
    assert error.status_code == 403


def test_classifies_drm_and_paid_content_as_platform_restricted() -> None:
    for message in ["DRM protected content", "premium only video"]:
        error = YtDlpAdapter().map_parse_error(RuntimeError(message))

        assert error.code == "platform_restricted"
        assert error.status_code == 403


def test_classifies_rate_limit_as_platform_rate_limited() -> None:
    error = YtDlpAdapter().map_parse_error(RuntimeError("HTTP Error 429: Too Many Requests"))

    assert error.code == "platform_rate_limited"
    assert error.status_code == 429


def test_classifies_unsupported_url_as_unsupported_platform() -> None:
    error = YtDlpAdapter().map_parse_error(RuntimeError("Unsupported URL: https://example.invalid/video/1"))

    assert error.code == "unsupported_platform"
    assert error.status_code == 422


def test_classifies_temporary_network_error_as_platform_unavailable() -> None:
    error = YtDlpAdapter().map_parse_error(RuntimeError("The read operation timed out"))

    assert error.code == "platform_unavailable"
    assert error.status_code == 503


def test_classifies_captcha_as_platform_rate_limited() -> None:
    """验证码触发应映射为限流错误。"""
    error = YtDlpAdapter().map_parse_error(RuntimeError("Captcha required, please solve the captcha"))

    assert error.code == "platform_rate_limited"
    assert error.status_code == 429


def test_classifies_chinese_membership_as_platform_restricted() -> None:
    """中文会员/付费提示应映射为访问限制。"""
    for message in ["仅限会员观看", "此视频为付费内容"]:
        error = YtDlpAdapter().map_parse_error(RuntimeError(message))

        assert error.code == "platform_restricted", f"message={message} code={error.code}"
        assert error.status_code == 403


def test_classifies_unknown_error_as_parse_failed() -> None:
    """无法识别的异常应回退到 parse_failed。"""
    error = YtDlpAdapter().map_parse_error(RuntimeError("something completely unexpected happened"))

    assert error.code == "parse_failed"
    assert error.status_code == 422


def test_error_response_does_not_leak_sensitive_params() -> None:
    """错误消息不应泄露 URL 中的敏感参数。"""
    sensitive_tokens = [
        "token=abc123secret",
        "signature=sig987private",
        "auth=bearer_token_here",
        "cookie=session_id_value",
        "key=api_key_value",
        "access_token=oauth_token_value",
        "session=sess_abc123",
    ]
    error = YtDlpAdapter().map_parse_error(RuntimeError("Unsupported URL: https://example.com/video"))

    for secret in sensitive_tokens:
        assert secret not in error.message, f"error message leaks: {secret}"
