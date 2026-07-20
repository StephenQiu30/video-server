"""URL validation and SSRF guards for media inspection.

The policy is deliberately synchronous so it can also be used from the
yt-dlp worker thread.  Every URL (including redirect targets) must go through
the same validation path before it is handed to an HTTP client.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UrlPolicyError(ValueError):
    """Raised when a URL is outside the public HTTP(S) boundary."""


@dataclass(frozen=True, slots=True)
class ValidatedUrl:
    """Canonical URL and the host used for SSRF resolution."""

    value: str
    host: str
    port: int


def _reject_ip(address: str) -> None:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as exc:
        raise UrlPolicyError("DNS returned an invalid address") from exc
    # ``is_global`` excludes loopback, link-local, private, reserved,
    # multicast and unspecified ranges for both IPv4 and IPv6.
    if not ip.is_global:
        raise UrlPolicyError("URL resolves to a non-public address")


def _resolve_public(host: str, port: int) -> None:
    try:
        answers = socket.getaddrinfo(
            host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
    except OSError as exc:
        raise UrlPolicyError("URL host could not be resolved") from exc
    if not answers:
        raise UrlPolicyError("URL host could not be resolved")
    for answer in answers:
        _reject_ip(str(answer[4][0]))


def _canonical_parts(value: str) -> tuple[SplitResult, int]:
    if not isinstance(value, str) or not value.strip():
        raise UrlPolicyError("URL is required")
    if len(value) > 2048:
        raise UrlPolicyError("URL is too long")
    # Whitespace/control characters can be interpreted differently by
    # different HTTP stacks and are never useful for a page URL.
    if any(ord(char) < 0x20 or char.isspace() for char in value):
        raise UrlPolicyError("URL contains whitespace or control characters")
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise UrlPolicyError("URL is malformed") from exc
    if parts.scheme.lower() not in {"http", "https"}:
        raise UrlPolicyError("only HTTP(S) URLs are supported")
    raw_host = parts.hostname
    if not raw_host:
        raise UrlPolicyError("URL host is required")
    if parts.username is not None or parts.password is not None:
        raise UrlPolicyError("URL user information is not allowed")
    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise UrlPolicyError("URL port is invalid") from exc
    if port not in {80, 443}:
        raise UrlPolicyError("URL port is not allowed")
    # Fragments are never sent to an origin and make redirect comparisons
    # ambiguous, so reject them instead of silently dropping user input.
    if parts.fragment:
        raise UrlPolicyError("URL fragments are not allowed")
    return parts, port


def validate_url(value: str, *, resolve: bool = True) -> ValidatedUrl:
    """Validate one URL and optionally resolve all DNS answers.

    ``resolve=False`` is useful only for parsing a value before an injected
    resolver performs the same check.  Production callers should keep the
    default and resolve every initial/redirect URL.
    """

    parts, port = _canonical_parts(value)
    raw_host = parts.hostname
    if not raw_host:
        raise UrlPolicyError("URL host is required")
    host = raw_host.lower().rstrip(".")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        _reject_ip(str(literal))
    elif resolve:
        _resolve_public(host, port)
    canonical = urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc,
            parts.path or "/",
            parts.query,
            "",
        )
    )
    return ValidatedUrl(value=canonical, host=host, port=port)


def assert_safe_url(value: str, *, resolve: bool = True) -> str:
    """Return a canonical URL or raise :class:`UrlPolicyError`."""

    return validate_url(value, resolve=resolve).value


class URLPolicy:
    """Small injectable policy object used by extractors and redirect hooks."""

    def __init__(
        self, *, resolver: Callable[[str, int], Iterable[str]] | None = None
    ) -> None:
        self._resolver = resolver

    def validate(self, value: str) -> ValidatedUrl:
        if self._resolver is None:
            return validate_url(value)
        parts, port = _canonical_parts(value)
        raw_host = parts.hostname
        if not raw_host:
            raise UrlPolicyError("URL host is required")
        host = raw_host.lower().rstrip(".")
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            _reject_ip(str(literal))
        else:
            addresses = self._resolver(host, port)
            if not addresses:
                raise UrlPolicyError("URL host could not be resolved")
            for address in addresses:
                _reject_ip(str(address))
        return validate_url(value, resolve=False)

    def check_redirect(self, value: str) -> str:
        """Validate a redirect target with the exact same SSRF rules."""

        return self.validate(value).value


# The plan calls this module ``url_policy``; ``policy.py`` re-exports these
# symbols for callers that use the shorter name.
__all__ = [
    "URLPolicy",
    "UrlPolicyError",
    "ValidatedUrl",
    "assert_safe_url",
    "validate_url",
]
