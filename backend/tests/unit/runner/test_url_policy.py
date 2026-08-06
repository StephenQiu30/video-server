from __future__ import annotations

import pytest
from app.runner.url_policy import UrlPolicyError, validate_media_url


@pytest.mark.parametrize(
    ("value", "hostname", "port"),
    [
        ("https://media.example.com/video?id=1", "media.example.com", 443),
        ("https://media.example.com:443/video", "media.example.com", 443),
        ("http://media.example.com:80/video", "media.example.com", 80),
        ("https://\u4f8b\u5b50.\u6d4b\u8bd5/video", "xn--fsqu00a.xn--0zwm56d", 443),
    ],
)
def test_accepts_strict_public_http_urls(
    value: str,
    hostname: str,
    port: int,
) -> None:
    validated = validate_media_url(value)

    assert validated.value == value
    assert validated.hostname == hostname
    assert validated.port == port


@pytest.mark.parametrize(
    "value",
    [
        "ftp://media.example.com/video",
        "https://user:pass@media.example.com/video",
        "https://@media.example.com/video",
        "https://127.0.0.1/video",
        "https://127.1/video",
        "https://0177.0.0.1/video",
        "https://0x7f.0.0.1/video",
        "https://[::1]/video",
        "https://localhost/video",
        "https://api.localhost/video",
        "https://media.local/video",
        "https://single-label/video",
        "https://media.example.com:8443/video",
        "https://media.example.com:/video",
        " https://media.example.com/video",
        "https://media.example.com\\@127.0.0.1/video",
        "https://media.example.com/\nvideo",
        "https:///video",
    ],
)
def test_rejects_unsafe_or_ambiguous_urls(value: str) -> None:
    with pytest.raises(UrlPolicyError):
        validate_media_url(value)


def test_rejects_excessively_long_url() -> None:
    with pytest.raises(UrlPolicyError):
        validate_media_url(f"https://media.example.com/{'x' * 4096}")
