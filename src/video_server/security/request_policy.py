"""Exact Host, Origin, Fetch Metadata, and JSON request policy."""

from __future__ import annotations

import re
from dataclasses import dataclass

from video_server.errors import DomainError
from video_server.security.trusted_config import (
    validate_trusted_api_authority,
    validate_trusted_web_origin,
)

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_HTTP_TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


@dataclass(frozen=True, slots=True)
class RequestMetadata:
    method: str
    authority: str | None
    origin: str | None
    fetch_site: str | None
    content_type: str | None


class RequestPolicy:
    """Validate deployment-owned request metadata without authenticating a user."""

    def __init__(self, *, trusted_api_authority: str, trusted_web_origin: str) -> None:
        self._trusted_api_authority = validate_trusted_api_authority(trusted_api_authority)
        self._trusted_web_origin = validate_trusted_web_origin(trusted_web_origin)

    def validate(self, metadata: RequestMetadata) -> None:
        if not isinstance(metadata, RequestMetadata):
            raise TypeError("metadata must be RequestMetadata")
        if metadata.authority != self._trusted_api_authority:
            raise _origin_error()
        if metadata.method in _UNSAFE_METHODS:
            if metadata.origin != self._trusted_web_origin or metadata.fetch_site != "same-origin":
                raise _origin_error()
            if not _is_application_json(metadata.content_type):
                raise _content_type_error()


def _is_application_json(value: object) -> bool:
    if not isinstance(value, str) or any(_is_control(char) for char in value):
        return False
    segments = _split_quoted(value, ";")
    if segments is None:
        return False
    media_type, *parameters = segments
    if media_type.strip().casefold() != "application/json":
        return False
    names: set[str] = set()
    for parameter in parameters:
        name, separator, parameter_value = parameter.partition("=")
        canonical_name = name.strip().casefold()
        if (
            not separator
            or not _HTTP_TOKEN.fullmatch(name.strip())
            or canonical_name in names
            or not _is_parameter_value(parameter_value.strip())
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


def _origin_error() -> DomainError:
    return DomainError("REQUEST_ORIGIN_REJECTED", "Request origin is not allowed.")


def _content_type_error() -> DomainError:
    return DomainError("CONTENT_TYPE_UNSUPPORTED", "Content type is not supported.")
