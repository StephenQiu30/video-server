from __future__ import annotations

from app.api.auth_dependencies import _client_host, _rate_limit_operation
from app.infrastructure.rate_limiter import _POLICIES
from starlette.requests import Request


class _Request:
    def __init__(self, method: str, path: str) -> None:
        self.method = method
        self.url = _URL(path)


class _URL:
    def __init__(self, path: str) -> None:
        self.path = path


def _request(method: str, path: str) -> object:
    return _Request(method, path)


def _network_request(peer: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": (peer, 12345),
            "server": ("testserver", 80),
        }
    )


def test_client_host_uses_the_nearest_untrusted_forwarded_address() -> None:
    trusted = ("127.0.0.0/8", "172.30.99.10/32")
    request = _network_request(
        "172.30.99.10", "203.0.113.200, 198.51.100.24, 172.30.99.10"
    )

    assert _client_host(request, trusted) == "198.51.100.24"


def test_client_host_ignores_forwarding_headers_from_untrusted_peers() -> None:
    request = _network_request("198.51.100.24", "203.0.113.200")

    assert _client_host(request, ("127.0.0.0/8",)) == "198.51.100.24"


def test_client_host_fails_closed_for_a_malformed_forwarding_chain() -> None:
    request = _network_request("127.0.0.1", "203.0.113.200, invalid")

    assert _client_host(request, ("127.0.0.0/8",)) == "127.0.0.1"


def test_inspection_post_is_rate_limited() -> None:
    assert _rate_limit_operation(_request("POST", "/api/inspections")) == "inspect"
    assert (
        _rate_limit_operation(_request("POST", "/api/source-discoveries")) == "inspect"
    )


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


def test_media_import_mutations_are_rate_limited() -> None:
    resource = "2a11fb32-0e3d-4a2b-8a5d-0f2d1a4f9f4e"

    assert (
        _rate_limit_operation(_request("POST", "/api/media-imports")) == "media_import"
    )
    assert (
        _rate_limit_operation(
            _request("POST", f"/api/media-imports/{resource}/upload-sessions")
        )
        == "media_import_upload"
    )
    assert (
        _rate_limit_operation(
            _request("POST", f"/api/media-imports/{resource}/complete")
        )
        == "media_import_upload"
    )


def test_media_import_rate_limit_operations_have_admission_policies() -> None:
    assert {"media_import", "media_import_upload"} <= _POLICIES.keys()


def test_document_import_mutations_have_admission_policies() -> None:
    resource = "2a11fb32-0e3d-4a2b-8a5d-0f2d1a4f9f4e"

    assert _rate_limit_operation(_request("POST", "/api/documents")) == (
        "document_import"
    )
    assert (
        _rate_limit_operation(
            _request("POST", f"/api/documents/{resource}/upload-sessions")
        )
        == "document_import_upload"
    )
    assert (
        _rate_limit_operation(_request("POST", f"/api/documents/{resource}/complete"))
        == "document_import_upload"
    )
    assert {"document_import", "document_import_upload"} <= _POLICIES.keys()
    assert (
        _rate_limit_operation(_request("DELETE", f"/api/documents/{resource}"))
        == "document_import"
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
