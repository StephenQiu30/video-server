"""Canonical URL and resolved-address security boundary."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterable
from urllib.parse import unquote_to_bytes, urlsplit, urlunsplit

import idna

from video_server.errors import DomainError


class SourceURLValidationError(DomainError):
    """A submitted URL or resolved address violates the source boundary."""


_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_PATH_SAFE = _UNRESERVED | frozenset("/!$&'()*+,;=:@")
_QUERY_SAFE = _UNRESERVED | frozenset("!$&'()*+,;=:/?@")
_IPV4_COMPATIBLE = ipaddress.IPv6Network("::/96")
_NAT64_WELL_KNOWN = ipaddress.IPv6Network("64:ff9b::/96")


def _invalid(detail: str = "The source URL is invalid.") -> SourceURLValidationError:
    return SourceURLValidationError("INVALID_URL", detail, field="/url")


def _unsafe(detail: str = "The source URL is not publicly reachable.") -> SourceURLValidationError:
    return SourceURLValidationError("UNSAFE_URL", detail, field="/url")


def _canonical_component(value: str, *, path: bool) -> str:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise _invalid()
    if path and ("\\" in value or re.search(r"(?i)%(?:2f|5c|00)", value)):
        raise _unsafe()

    cursor = 0
    while cursor < len(value):
        if value[cursor] == "%":
            if _PERCENT_ESCAPE.fullmatch(value[cursor : cursor + 3]) is None:
                raise _invalid()
            cursor += 3
        else:
            cursor += 1
    try:
        unquote_to_bytes(value).decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        raise _invalid() from None

    safe = _PATH_SAFE if path else _QUERY_SAFE
    canonical: list[str] = []
    cursor = 0
    while cursor < len(value):
        character = value[cursor]
        if character == "%":
            byte = int(value[cursor + 1 : cursor + 3], 16)
            decoded = chr(byte)
            canonical.append(decoded if decoded in _UNRESERVED else f"%{byte:02X}")
            cursor += 3
            continue
        if character in safe:
            canonical.append(character)
        else:
            canonical.extend(f"%{byte:02X}" for byte in character.encode("utf-8"))
        cursor += 1

    result = "".join(canonical)
    if path and any(segment in {".", ".."} for segment in result.split("/")):
        raise _unsafe()
    return result


def _canonical_host(hostname: str) -> str:
    host = hostname.removesuffix(".")
    if not host:
        raise _invalid()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise _unsafe()
    try:
        canonical = (
            idna.encode(
                host,
                uts46=True,
                transitional=False,
                std3_rules=True,
            )
            .decode("ascii")
            .lower()
        )
    except idna.IDNAError:
        raise _invalid() from None
    if "." not in canonical or canonical.endswith(".localhost"):
        raise _unsafe()
    return canonical


def canonicalize_source_url(url: str) -> str:
    """Return the canonical public HTTPS source URL or raise DomainError."""

    if not isinstance(url, str) or not url or "#" in url:
        raise _invalid()
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise _invalid()
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (UnicodeError, ValueError):
        raise _invalid() from None
    if parsed.scheme.lower() != "https" or not parsed.netloc or parsed.hostname is None:
        raise _invalid()
    if parsed.username is not None or parsed.password is not None:
        raise _unsafe()
    if "\\" in parsed.netloc or "[" in parsed.netloc or "]" in parsed.netloc:
        raise _unsafe()
    if port not in {None, 443}:
        raise _unsafe()

    host = _canonical_host(parsed.hostname)
    path = _canonical_component(parsed.path or "/", path=True)
    query = _canonical_component(parsed.query, path=False)
    return urlunsplit(("https", host, path, query, ""))


def _translated_ipv4(address: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    if address in _IPV4_COMPATIBLE or address in _NAT64_WELL_KNOWN:
        return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    return None


def validate_public_addresses(addresses: Iterable[str]) -> tuple[str, ...]:
    """Validate every resolved address and return a stable tuple."""

    stable = tuple(addresses)
    if not stable:
        raise _unsafe("The source hostname did not resolve to a public address.")
    for address in stable:
        try:
            parsed = ipaddress.ip_address(address)
        except (TypeError, ValueError):
            raise _unsafe("The source hostname resolved to an invalid address.") from None
        translated = _translated_ipv4(parsed) if isinstance(parsed, ipaddress.IPv6Address) else None
        if (
            parsed.is_multicast
            or not parsed.is_global
            or (isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None)
            or (translated is not None and (translated.is_multicast or not translated.is_global))
        ):
            raise _unsafe()
    return stable
