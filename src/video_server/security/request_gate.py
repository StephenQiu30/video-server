"""Pure local-installation request authorization boundary."""

from __future__ import annotations

import ipaddress
import re
import secrets
from dataclasses import dataclass
from urllib.parse import urlsplit

from video_server.errors import DomainError

_MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_HTTP_TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_BEARER_TOKEN = re.compile(r"^[A-Za-z0-9._~+/-]+=*$")


@dataclass(frozen=True, slots=True)
class InstallationPrincipal:
    owner_id: str
    bearer_token: str


@dataclass(frozen=True, slots=True)
class RequestContext:
    method: str
    authority: str | None
    authorization: str | None
    origin: str | None
    fetch_site: str | None
    content_type: str | None = None


class RequestGate:
    """Authorize one BFF request without exposing the installation token."""

    def __init__(
        self,
        principal: InstallationPrincipal,
        *,
        web_origin: str,
        api_authority: str,
    ) -> None:
        if not _nonempty(principal.owner_id) or not _is_bearer_token(principal.bearer_token):
            raise _authentication_error()
        if not _is_loopback_origin(web_origin) or not _is_loopback_authority(api_authority):
            raise _origin_error()

        self._owner_id = principal.owner_id
        self._bearer_token = principal.bearer_token
        self._web_origin = web_origin
        self._api_authority = api_authority

    def authorize(self, context: RequestContext) -> str:
        """Return the immutable owner ID or raise a canonical DomainError."""

        if (
            context.authority != self._api_authority
            or context.origin != self._web_origin
            or context.fetch_site != "same-origin"
        ):
            raise _origin_error()

        authorization = context.authorization
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise _authentication_error()
        presented_token = authorization.removeprefix("Bearer ")
        if not _is_bearer_token(presented_token) or not secrets.compare_digest(
            presented_token,
            self._bearer_token,
        ):
            raise _authentication_error()

        if context.method in _MUTATION_METHODS and not _is_application_json(context.content_type):
            raise _content_type_error()
        return self._owner_id


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_bearer_token(value: object) -> bool:
    return isinstance(value, str) and _BEARER_TOKEN.fullmatch(value) is not None


def _is_loopback_origin(origin: object) -> bool:
    if not isinstance(origin, str):
        return False
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.path or parsed.query or parsed.fragment or parsed.scheme != "http":
        return False
    return _is_loopback_authority(parsed.netloc) and origin == f"http://{parsed.netloc}"


def _is_loopback_authority(authority: object) -> bool:
    if not isinstance(authority, str) or not authority:
        return False
    try:
        parsed = urlsplit(f"http://{authority}")
        host = parsed.hostname
        port = parsed.port
        address = ipaddress.ip_address(host) if host is not None else None
    except ValueError:
        return False
    if (
        parsed.netloc != authority
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or address is None
        or not address.is_loopback
        or port is None
    ):
        return False
    canonical_host = f"[{address.compressed}]" if address.version == 6 else address.compressed
    return authority == f"{canonical_host}:{port}"


def _is_application_json(content_type: object) -> bool:
    if not isinstance(content_type, str) or any(_is_control(char) for char in content_type):
        return False
    segments = _split_quoted(content_type, ";")
    if segments is None:
        return False
    media_type, *parameters = segments
    if media_type.strip().casefold() != "application/json":
        return False
    names: set[str] = set()
    for parameter in parameters:
        name, separator, value = parameter.partition("=")
        canonical_name = name.strip().casefold()
        if (
            not separator
            or not _HTTP_TOKEN.fullmatch(name.strip())
            or canonical_name in names
            or not _is_parameter_value(value.strip())
        ):
            return False
        names.add(canonical_name)
    return True


def _is_control(char: str) -> bool:
    return ord(char) < 0x20 or ord(char) == 0x7F


def _split_quoted(value: str, delimiter: str) -> list[str] | None:
    parts: list[str] = []
    start = 0
    quoted = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char == delimiter and not quoted:
            parts.append(value[start:index])
            start = index + 1
    if quoted or escaped:
        return None
    parts.append(value[start:])
    return parts


def _is_parameter_value(value: str) -> bool:
    if _HTTP_TOKEN.fullmatch(value):
        return True
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return False
    escaped = False
    for char in value[1:-1]:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return False
    return not escaped


def _authentication_error() -> DomainError:
    return DomainError("AUTHENTICATION_REQUIRED", "Authentication is required.")


def _origin_error() -> DomainError:
    return DomainError("REQUEST_ORIGIN_REJECTED", "Request origin is not allowed.")


def _content_type_error() -> DomainError:
    return DomainError("CONTENT_TYPE_UNSUPPORTED", "Content type is not supported.")
