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
SOURCE_URL = "https://owned.example/videos/trailer.mp4"


def _verify_operator(
    payload: dict[str, Any],
    trusted: Mapping[str, Any],
) -> Mapping[str, Any]:
    return verify_policy_dossier(
        sign_dossier(payload, key_id=OPERATOR_KEY_ID, seed=OPERATOR_SEED),
        trusted,
        operation="probe",
        source_url=SOURCE_URL,
        now=NOW,
    )


def _assert_blocked(error: pytest.ExceptionInfo[DomainError]) -> None:
    assert error.value.code == "SOURCE_POLICY_BLOCKED"


@pytest.mark.policy
@pytest.mark.security
def test_operator_dossier_cannot_predate_origin_grant_verification() -> None:
    trusted = trust_store(operator=True)
    trusted["keys"][0]["origin_grant"]["verified_at"] = "2026-07-18T01:00:00Z"

    with pytest.raises(DomainError) as error:
        _verify_operator(operator_payload(), trusted)

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.security
def test_operator_dossier_cannot_outlive_origin_grant() -> None:
    trusted = trust_store(operator=True)
    trusted["keys"][0]["origin_grant"]["expires_at"] = "2026-07-27T00:00:00Z"

    with pytest.raises(DomainError) as error:
        _verify_operator(operator_payload(), trusted)

    _assert_blocked(error)
