"""Validation for exact, operator-approved federated Provider hosts."""

from __future__ import annotations

import re

_DOMAIN = re.compile(
    r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


def validated_instance_hosts(hosts: frozenset[str]) -> frozenset[str]:
    normalized = frozenset(host.strip().lower() for host in hosts)
    if len(normalized) != len(hosts) or any(
        _DOMAIN.fullmatch(host) is None for host in normalized
    ):
        raise ValueError("PeerTube instance allowlist contains an invalid host")
    return normalized
