"""Runtime configuration invariants."""

from __future__ import annotations


def validate_bind_host(host: str, *, principal_provider_configured: bool) -> str:
    """Accept loopback binding or require an explicit principal provider."""

    raise NotImplementedError("bind host validation is not implemented")
