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
