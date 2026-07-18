"""Canonical URL and resolved-address security boundary."""

from __future__ import annotations

from collections.abc import Iterable


def canonicalize_source_url(url: str) -> str:
    """Return the canonical public HTTPS source URL or raise DomainError."""

    raise NotImplementedError("source URL canonicalization is not implemented")


def validate_public_addresses(addresses: Iterable[str]) -> tuple[str, ...]:
    """Validate every resolved address and return a stable tuple."""

    raise NotImplementedError("resolved-address validation is not implemented")
