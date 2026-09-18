from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_NUMERIC_HOST_LABEL = re.compile(r"(?:0x[0-9a-f]+|[0-9]+)")
_LOCAL_SUFFIXES = (".localhost", ".local", ".localdomain", ".internal", ".home.arpa")
_PORTS = {"http": 80, "https": 443}


class UrlPolicyError(ValueError):
    """The submitted URL cannot safely enter the media runner."""


@dataclass(frozen=True, slots=True)
class ValidatedMediaUrl:
    value: str
    scheme: str
    hostname: str
    port: int


def validate_media_url(value: str, *, max_length: int = 4096) -> ValidatedMediaUrl:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise UrlPolicyError("URL length is invalid")
    if value != value.strip() or "\\" in value or _contains_control(value):
        raise UrlPolicyError("URL contains ambiguous characters")

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (UnicodeError, ValueError) as exc:
        raise UrlPolicyError("URL authority is invalid") from exc

    scheme = parsed.scheme.lower()
    if scheme not in _PORTS or not parsed.netloc:
        raise UrlPolicyError("only HTTP(S) URLs are accepted")
    if "@" in parsed.netloc:
        raise UrlPolicyError("userinfo is forbidden")
    if parsed.netloc.endswith(":"):
        raise UrlPolicyError("empty port is forbidden")
    if parsed.hostname is None:
        raise UrlPolicyError("hostname is required")

    hostname = _normalize_hostname(parsed.hostname)
    expected_port = _PORTS[scheme]
    if port is not None and port != expected_port:
        raise UrlPolicyError("non-standard port is forbidden")

    return ValidatedMediaUrl(
        value=value,
        scheme=scheme,
        hostname=hostname,
        port=port or expected_port,
    )


def _normalize_hostname(hostname: str) -> str:
    try:
        normalized = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UrlPolicyError("hostname is invalid") from exc

    if not normalized or len(normalized) > 253:
        raise UrlPolicyError("hostname is invalid")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise UrlPolicyError("IP literals are forbidden")

    labels = normalized.split(".")
    if "." not in normalized or normalized == "localhost":
        raise UrlPolicyError("local or single-label hostnames are forbidden")
    if all(_NUMERIC_HOST_LABEL.fullmatch(label) is not None for label in labels):
        raise UrlPolicyError("legacy numeric IP literals are forbidden")
    if any(normalized.endswith(suffix) for suffix in _LOCAL_SUFFIXES):
        raise UrlPolicyError("local hostnames are forbidden")
    if any(_HOST_LABEL.fullmatch(label) is None for label in labels):
        raise UrlPolicyError("hostname labels are invalid")
    return normalized


def _contains_control(value: str) -> bool:
    return any(ord(character) <= 32 or ord(character) == 127 for character in value)
