"""Runtime configuration invariants."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from typing import cast

import idna


def _canonical_host(host: str) -> tuple[str, bool]:
    if not host or host == "*" or host != host.strip() or "%" in host:
        raise ValueError("bind host is empty or invalid")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        candidate = host[:-1] if host.endswith(".") else host
        if not candidate or candidate.endswith("."):
            raise ValueError("bind host is empty or invalid") from None
        try:
            canonical = idna.encode(candidate, uts46=False, std3_rules=True).decode("ascii")
        except idna.IDNAError as error:
            raise ValueError("bind host is invalid") from error
        canonical = canonical.lower()
        return canonical, False

    return address.compressed.lower(), address.is_loopback


def _validate_principal_provider(provider: object | None) -> None:
    validator = getattr(provider, "validate_startup", None)
    if not callable(validator):
        raise ValueError("non-loopback binding requires a principal provider")
    try:
        result = cast(Callable[[], object], validator)()
    except Exception as error:
        raise ValueError("principal provider startup validation failed") from error
    if result is not True:
        raise ValueError("principal provider did not validate startup")


def validate_bind_host(host: str, *, principal_provider: object | None) -> str:
    """Accept loopback binding or require an explicit principal provider."""

    canonical, is_loopback = _canonical_host(host)
    if not is_loopback:
        _validate_principal_provider(principal_provider)
    return canonical
