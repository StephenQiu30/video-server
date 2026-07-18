"""Canonical trusted Host and web-origin configuration validation."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

import idna


def validate_trusted_api_authority(value: object) -> str:
    """Return one canonical host[:port] authority or fail closed."""

    if not isinstance(value, str):
        raise TypeError("trusted_api_authority must be a string")
    if not value or value != value.strip():
        raise ValueError("trusted_api_authority must be canonical")
    try:
        parsed = urlsplit(f"//{value}")
        port = parsed.port
    except ValueError as error:
        raise ValueError("trusted_api_authority must be canonical") from error
    if (
        parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname is None
        or port == 0
    ):
        raise ValueError("trusted_api_authority must be one host[:port]")
    host, ipv6 = _canonical_host(parsed.hostname)
    canonical = f"[{host}]" if ipv6 else host
    if port is not None:
        canonical = f"{canonical}:{port}"
    if value != canonical:
        raise ValueError("trusted_api_authority must be canonical")
    return value


def validate_trusted_web_origin(value: object) -> str:
    """Allow canonical HTTPS, plus HTTP only for literal loopback origins."""

    if not isinstance(value, str):
        raise TypeError("trusted_web_origin must be a string")
    if not value or value != value.strip():
        raise ValueError("trusted_web_origin must be canonical")
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise ValueError("trusted_web_origin must be canonical") from error
    if (
        parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname is None
    ):
        raise ValueError("trusted_web_origin must be an exact origin")
    authority = validate_trusted_api_authority(parsed.netloc)
    if (parsed.scheme == "https" and parsed.port == 443) or (
        parsed.scheme == "http" and parsed.port == 80
    ):
        raise ValueError("trusted_web_origin must omit the default port")
    canonical = f"{parsed.scheme}://{authority}"
    if value != canonical:
        raise ValueError("trusted_web_origin must be canonical")
    if parsed.scheme == "https":
        return value
    if parsed.scheme == "http" and _is_literal_loopback(parsed.hostname):
        return value
    raise ValueError("trusted_web_origin must use HTTPS or loopback HTTP")


def _canonical_host(host: str) -> tuple[str, bool]:
    if "%" in host:
        raise ValueError("scoped IPv6 addresses are not canonical authorities")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if host.replace(".", "").isdigit():
            raise ValueError("numeric host must be a canonical IP address") from None
        try:
            canonical = idna.encode(host, uts46=False, std3_rules=True).decode("ascii")
        except idna.IDNAError as error:
            raise ValueError("host must be a valid DNS name or IP address") from error
        if canonical != host:
            raise ValueError("DNS host must be canonical") from None
        return canonical, False
    return address.compressed, address.version == 6


def _is_literal_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
