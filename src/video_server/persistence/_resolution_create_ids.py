"""Opaque identifiers for source-resolution aggregates."""

from __future__ import annotations

import re
import secrets

_SAFE_IDS = {
    "job": re.compile(r"^job_[A-Za-z0-9_-]{1,124}$"),
    "res": re.compile(r"^res_[A-Za-z0-9_-]{1,124}$"),
}


def validate_resolution_id(value: object, *, kind: str) -> str:
    pattern = _SAFE_IDS.get(kind)
    if pattern is None or not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{kind} id must use the stable safe identifier alphabet")
    return value


def new_resolution_id(kind: str) -> str:
    return validate_resolution_id(f"{kind}_{secrets.token_urlsafe(18)}", kind=kind)
