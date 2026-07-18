from __future__ import annotations

import pytest

from video_server.errors import DomainError
from video_server.source.urls import (
    canonicalize_source_url,
    validate_public_addresses,
)


def _assert_code(error: pytest.ExceptionInfo[DomainError], code: str) -> None:
    assert error.value.code == code


@pytest.mark.security
def test_canonicalizes_https_host_default_port_idna_and_unreserved_path() -> None:
    url = "https://bücher.EXAMPLE.:443/%7eclips/%41.mp4?token=a%2fb"

    assert canonicalize_source_url(url) == (
        "https://xn--bcher-kva.example/~clips/A.mp4?token=a%2Fb"
    )


@pytest.mark.security
@pytest.mark.parametrize(
    "url",
    [
        "http://media.example/video.mp4",
        "ftp://media.example/video.mp4",
        "//media.example/video.mp4",
        "not-a-url",
        "https://media.example/video.mp4#fragment",
    ],
)
def test_rejects_non_https_or_ambiguous_urls(url: str) -> None:
    with pytest.raises(DomainError) as error:
        canonicalize_source_url(url)

    _assert_code(error, "INVALID_URL")


@pytest.mark.security
@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@media.example/video.mp4",
        "https://127.0.0.1/video.mp4",
        "https://[::1]/video.mp4",
        "https://media.example:444/video.mp4",
        "https://media.example/a/../video.mp4",
        "https://media.example/a/./video.mp4",
        "https://media.example/a/%2e%2e/video.mp4",
        "https://media.example/a%2Fvideo.mp4",
        "https://media.example/a%2fvideo.mp4",
        "https://media.example/a%5Cvideo.mp4",
        "https://media.example/a\\video.mp4",
        "https://media.example/a%00video.mp4",
    ],
)
def test_rejects_userinfo_ip_port_and_unsafe_paths(url: str) -> None:
    with pytest.raises(DomainError) as error:
        canonicalize_source_url(url)

    _assert_code(error, "UNSAFE_URL")


@pytest.mark.security
@pytest.mark.parametrize(
    "url",
    [
        "https://media.example/%",
        "https://media.example/%GG",
        "https://media.example/%C3%28",
    ],
)
def test_rejects_invalid_percent_or_utf8_path(url: str) -> None:
    with pytest.raises(DomainError) as error:
        canonicalize_source_url(url)

    _assert_code(error, "INVALID_URL")


@pytest.mark.security
def test_accepts_only_when_every_resolved_address_is_public() -> None:
    addresses = ["8.8.8.8", "2606:4700:4700::1111"]

    assert validate_public_addresses(addresses) == tuple(addresses)


@pytest.mark.security
@pytest.mark.parametrize(
    "address",
    [
        "0.0.0.0",
        "10.0.0.1",
        "100.64.0.1",
        "127.0.0.1",
        "169.254.1.1",
        "192.0.2.1",
        "224.0.0.1",
        "255.255.255.255",
        "::",
        "::1",
        "fc00::1",
        "fe80::1",
        "ff02::1",
        "2001:db8::1",
        "::ffff:8.8.8.8",
    ],
)
def test_rejects_every_non_public_or_ipv4_mapped_address(address: str) -> None:
    with pytest.raises(DomainError) as error:
        validate_public_addresses([address])

    _assert_code(error, "UNSAFE_URL")


@pytest.mark.security
def test_rejects_mixed_dns_answer_if_any_address_is_not_public() -> None:
    with pytest.raises(DomainError) as error:
        validate_public_addresses(["8.8.8.8", "127.0.0.1"])

    _assert_code(error, "UNSAFE_URL")
