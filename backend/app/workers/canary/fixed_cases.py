"""Versioned public diagnostics; production canary URLs remain Secret-configured."""

from __future__ import annotations

from pathlib import Path

from app.workers.canary.targets import (
    ProviderCanaryTarget,
    parse_canary_targets,
)
from pydantic import SecretStr

_CASES = Path(__file__).with_name("fixed_public_cases.json")


def fixed_public_diagnostic_targets() -> tuple[ProviderCanaryTarget, ...]:
    return parse_canary_targets(SecretStr(_CASES.read_text(encoding="utf-8")))
