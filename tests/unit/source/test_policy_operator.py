from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.unit.source._policy_samples import (
    OPERATOR_KEY_ID,
    OPERATOR_SEED,
    operator_payload,
    sign_dossier,
    trust_store,
)
from video_server.errors import DomainError
from video_server.source.policies import verify_policy_dossier

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def _verify_operator(
    payload: dict[str, Any],
    trusted: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    dossier = sign_dossier(payload, key_id=OPERATOR_KEY_ID, seed=OPERATOR_SEED)
    return verify_policy_dossier(
        dossier,
        trust_store(operator=True) if trusted is None else trusted,
        operation="probe",
        source_url="https://owned.example/videos/trailer.mp4",
        now=NOW,
    )


def _assert_blocked(error: pytest.ExceptionInfo[DomainError]) -> None:
    assert error.value.code == "SOURCE_POLICY_BLOCKED"


@pytest.mark.policy
def test_operator_dossier_requires_current_origin_control_grant() -> None:
    verified = _verify_operator(operator_payload())

    assert verified["signer_kind"] == "operator"
    trusted = trust_store(operator=True)
    trusted["keys"][0].pop("origin_grant")
    with pytest.raises(DomainError) as missing_error:
        _verify_operator(operator_payload(), trusted)
    _assert_blocked(missing_error)


@pytest.mark.policy
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("expires_at", "2026-07-18T11:59:59Z"),
        ("proof_sha256", "9" * 64),
        ("origin", "https://other.example"),
    ],
)
def test_operator_origin_grant_must_be_current_and_match_proof_and_origin(
    field: str,
    value: str,
) -> None:
    trusted = trust_store(operator=True)
    trusted["keys"][0]["origin_grant"][field] = value

    with pytest.raises(DomainError) as error:
        _verify_operator(operator_payload(), trusted)

    _assert_blocked(error)


@pytest.mark.policy
def test_operator_dossier_cannot_exceed_trusted_scope() -> None:
    payload = operator_payload()
    payload["scope"] = [{"origin": "https://owned.example", "path_match": "prefix", "path": "/"}]

    with pytest.raises(DomainError) as error:
        _verify_operator(payload)

    _assert_blocked(error)


@pytest.mark.policy
def test_operator_dossier_expiry_cannot_exceed_thirty_days() -> None:
    payload = operator_payload()
    payload["expires_at"] = "2026-08-18T00:00:01Z"

    with pytest.raises(DomainError) as error:
        _verify_operator(payload)

    _assert_blocked(error)
