from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.unit.source._policy_samples import (
    OPERATOR_KEY_ID,
    OPERATOR_SEED,
    operator_payload,
    project_payload,
    sign_dossier,
    trust_store,
)
from video_server.errors import DomainError
from video_server.source.policies import verify_policy_dossier

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def _verify_operator(
    payload: dict[str, Any],
    trusted: Mapping[str, Any] | None = None,
    *,
    source_url: str = "https://owned.example/videos/trailer.mp4",
    now: datetime = NOW,
) -> Mapping[str, Any]:
    dossier = sign_dossier(payload, key_id=OPERATOR_KEY_ID, seed=OPERATOR_SEED)
    return verify_policy_dossier(
        dossier,
        trust_store(operator=True) if trusted is None else trusted,
        operation="probe",
        source_url=source_url,
        now=now,
    )


def _assert_blocked(error: pytest.ExceptionInfo[DomainError]) -> None:
    assert error.value.code == "SOURCE_POLICY_BLOCKED"


@pytest.mark.policy
@pytest.mark.security
def test_exact_scope_matches_canonical_path_and_ignores_query() -> None:
    dossier = sign_dossier(project_payload())
    source_url = "https://media.w3.org.:443/2010/05/sintel/trailer.mp4?token=a%2fb"

    verified = verify_policy_dossier(
        dossier,
        trust_store(),
        operation="probe",
        source_url=source_url,
        now=NOW,
    )

    assert verified["policy_id"] == "w3c-sintel"


@pytest.mark.policy
@pytest.mark.security
@pytest.mark.parametrize(
    "source_url",
    [
        "https://other.example/2010/05/sintel/trailer.mp4",
        "https://media.w3.org/2010/05/sintel/other.mp4",
        "https://media.w3.org/2010/05/sintel/trailer.mp4/child",
    ],
)
def test_exact_scope_rejects_other_origin_or_path(source_url: str) -> None:
    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            sign_dossier(project_payload()),
            trust_store(),
            operation="probe",
            source_url=source_url,
            now=NOW,
        )

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.security
def test_prefix_scope_respects_directory_segment_boundary() -> None:
    payload = operator_payload()

    assert (
        _verify_operator(
            payload,
            source_url="https://owned.example/videos/season-1/trailer.mp4",
        )["decision"]
        == "allow"
    )
    with pytest.raises(DomainError) as boundary_error:
        _verify_operator(
            payload,
            source_url="https://owned.example/videosness/trailer.mp4",
        )
    _assert_blocked(boundary_error)


@pytest.mark.policy
@pytest.mark.security
def test_prefix_scope_must_end_with_slash() -> None:
    payload = operator_payload()
    payload["scope"][0]["path"] = "/videos"

    with pytest.raises(DomainError) as error:
        _verify_operator(payload)

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.security
@pytest.mark.parametrize(
    "source_url",
    [
        "https://owned.example/videos/%2Fsecret.mp4",
        "https://owned.example/videos/%5csecret.mp4",
        "https://owned.example/videos/%2e%2e/secret.mp4",
        "https://owned.example/videos/../secret.mp4",
    ],
)
def test_scope_matching_never_normalizes_an_unsafe_path_into_scope(source_url: str) -> None:
    with pytest.raises(DomainError) as error:
        _verify_operator(operator_payload(), source_url=source_url)

    _assert_blocked(error)


@pytest.mark.policy
def test_rejects_expired_dossier() -> None:
    payload = project_payload()
    payload["expires_at"] = "2026-07-18T11:59:59Z"

    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            sign_dossier(payload),
            trust_store(),
            operation="probe",
            source_url="https://media.w3.org/2010/05/sintel/trailer.mp4",
            now=NOW,
        )

    _assert_blocked(error)


@pytest.mark.policy
def test_block_decision_never_authorizes_probe() -> None:
    payload = project_payload()
    payload["decision"] = "block"
    payload["permitted_operations"] = []
    trusted = trust_store()
    trusted["keys"][0]["allowed_decisions"] = ["allow", "block"]

    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            sign_dossier(payload),
            trusted,
            operation="probe",
            source_url="https://media.w3.org/2010/05/sintel/trailer.mp4",
            now=NOW,
        )

    _assert_blocked(error)


@pytest.mark.policy
def test_trust_scope_is_an_independent_upper_bound() -> None:
    trusted = trust_store()
    trusted["keys"][0]["scope"][0]["path"] = "/different.mp4"

    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            sign_dossier(project_payload()),
            trusted,
            operation="probe",
            source_url="https://media.w3.org/2010/05/sintel/trailer.mp4",
            now=NOW,
        )

    _assert_blocked(error)
