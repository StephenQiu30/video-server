"""Fail-closed trusted authority and web-origin configuration."""

from __future__ import annotations

import pytest

from video_server.security import RequestPolicy


@pytest.mark.parametrize(
    ("authority", "origin"),
    [
        ("127.0.0.1:8000", "http://127.0.0.1:3000"),
        ("[::1]:8000", "http://[::1]:3000"),
        ("api.example.test", "https://web.example.test"),
        ("api.example.test:443", "https://web.example.test:8443"),
    ],
)
def test_request_policy_accepts_canonical_deployment_configuration(
    authority: str,
    origin: str,
) -> None:
    assert (
        RequestPolicy(
            trusted_api_authority=authority,
            trusted_web_origin=origin,
        )
        is not None
    )


@pytest.mark.parametrize(
    "authority",
    [
        None,
        "",
        " ",
        "127.0.0.1:8000 ",
        "127.0.0.1:8000,127.0.0.1:8000",
        "http://127.0.0.1:8000",
        "user@api.example.test:443",
        "api.example.test/path",
        "api.example.test?query=1",
        "API.example.test:443",
        "api..example.test:443",
        "::1:8000",
        "api.example.test:0",
        "api.example.test:65536",
        "[fe80::1%eth0]:8000",
        "[fe80::1%25eth0]:8000",
    ],
)
def test_request_policy_rejects_noncanonical_or_joined_authority(
    authority: object,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        RequestPolicy(
            trusted_api_authority=authority,  # type: ignore[arg-type]
            trusted_web_origin="https://web.example.test",
        )


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        " ",
        "http://web.example.test",
        "ftp://web.example.test",
        "https://user@web.example.test",
        "https://web.example.test/",
        "https://web.example.test/path",
        "https://web.example.test?query=1",
        "https://web.example.test#fragment",
        "https://web.example.test,https://web.example.test",
        "HTTPS://web.example.test",
        "https://WEB.example.test",
        "http://localhost:3000",
        "http://0.0.0.0:3000",
        "https://web.example.test:443",
        "http://127.0.0.1:80",
        "https://[fe80::1%25eth0]",
    ],
)
def test_request_policy_rejects_unsafe_or_noncanonical_web_origin(origin: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        RequestPolicy(
            trusted_api_authority="api.example.test:443",
            trusted_web_origin=origin,  # type: ignore[arg-type]
        )
