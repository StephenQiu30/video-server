"""Signed source-policy dossier verification boundary."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any


def canonical_policy_payload(payload: Mapping[str, Any]) -> bytes:
    """Encode the signed payload as RFC 8785 JCS bytes."""

    raise NotImplementedError("policy canonicalization is not implemented")


def verify_policy_dossier(
    dossier: Mapping[str, Any],
    trust_store: Mapping[str, Any],
    *,
    operation: str,
    source_url: str,
    now: datetime,
) -> Mapping[str, Any]:
    """Verify signature, trust grant, lifecycle, scope, and operation."""

    raise NotImplementedError("policy verification is not implemented")
