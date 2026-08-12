from __future__ import annotations

from app.api.auth_dependencies import _rate_limit_operation


class _Request:
    def __init__(self, method: str, path: str) -> None:
        self.method = method
        self.url = _URL(path)


class _URL:
    def __init__(self, path: str) -> None:
        self.path = path


def _request(method: str, path: str) -> object:
    return _Request(method, path)


def test_inspection_post_is_rate_limited() -> None:
    assert _rate_limit_operation(_request("POST", "/api/inspections")) == "inspect"


def test_download_post_is_rate_limited() -> None:
    assert _rate_limit_operation(_request("POST", "/api/downloads")) == "download"


def test_analysis_post_is_rate_limited() -> None:
    assert (
        _rate_limit_operation(
            _request(
                "POST",
                "/api/downloads/2a11fb32-0e3d-4a2b-8a5d-0f2d1a4f9f4e/analyses",
            )
        )
        == "analysis"
    )


def test_download_retry_post_is_rate_limited() -> None:
    assert (
        _rate_limit_operation(
            _request(
                "POST", "/api/downloads/2a11fb32-0e3d-4a2b-8a5d-0f2d1a4f9f4e/retry"
            )
        )
        == "download_retry"
    )


def test_download_cancel_post_is_not_rate_limited() -> None:
    assert (
        _rate_limit_operation(
            _request(
                "POST", "/api/downloads/2a11fb32-0e3d-4a2b-8a5d-0f2d1a4f9f4e/cancel"
            )
        )
        is None
    )


def test_read_methods_are_not_rate_limited() -> None:
    assert _rate_limit_operation(_request("GET", "/api/downloads")) is None
    assert (
        _rate_limit_operation(
            _request("GET", "/api/downloads/2a11fb32-0e3d-4a2b-8a5d-0f2d1a4f9f4e/retry")
        )
        is None
    )
