from __future__ import annotations

import hashlib
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.unit.source._policy_samples import (
    PROJECT_KEY_ID,
    project_payload,
    sign_dossier,
    trust_store,
)
from video_server.errors import DomainError
from video_server.source.policies import canonical_policy_payload, verify_policy_dossier

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
SOURCE_URL = "https://media.w3.org/2010/05/sintel/trailer.mp4"


def _verify(
    dossier: Mapping[str, Any],
    trusted: Mapping[str, Any],
    *,
    operation: str = "probe",
    source_url: str = SOURCE_URL,
    now: datetime = NOW,
) -> Mapping[str, Any]:
    return verify_policy_dossier(
        dossier,
        trusted,
        operation=operation,
        source_url=source_url,
        now=now,
    )


def _assert_blocked(error: pytest.ExceptionInfo[DomainError]) -> None:
    assert error.value.code == "SOURCE_POLICY_BLOCKED"


@pytest.mark.policy
def test_canonical_payload_is_exact_rfc8785_utf8_bytes() -> None:
    payload = project_payload()
    canonical = canonical_policy_payload(payload)

    assert hashlib.sha256(canonical).hexdigest() == (
        "d4f6c2b543d1e46ef1fbd3465845910059191a9d9809b48ddaba430e74e939f5"
    )
    assert canonical.startswith(b'{"adapter":"direct_http","decision":"allow"')
    assert b'"reject_auth":true' in canonical
    assert b": " not in canonical
    assert b", " not in canonical


@pytest.mark.policy
def test_canonical_payload_does_not_depend_on_mapping_insertion_order() -> None:
    payload = project_payload()
    reversed_payload = dict(reversed(tuple(payload.items())))

    assert canonical_policy_payload(reversed_payload) == canonical_policy_payload(payload)


@pytest.mark.policy
def test_verifies_ed25519_signature_over_only_the_canonical_payload() -> None:
    payload = project_payload()
    verified = _verify(sign_dossier(payload), trust_store())

    assert verified["policy_id"] == "w3c-sintel"
    assert verified["permitted_operations"] == ["probe"]
    assert verified["name"] == "W3C Sintel"


@pytest.mark.policy
def test_rejects_payload_tampering_after_signature() -> None:
    dossier = sign_dossier(project_payload())
    dossier["payload"]["name"] = "Tampered"

    with pytest.raises(DomainError) as error:
        _verify(dossier, trust_store())

    _assert_blocked(error)


@pytest.mark.policy
def test_rejects_signature_key_that_is_not_in_trust_store() -> None:
    dossier = sign_dossier(project_payload())
    trusted = trust_store()
    trusted["keys"][0]["key_id"] = "different-key"

    with pytest.raises(DomainError) as error:
        _verify(dossier, trusted)

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.parametrize("status", ["disabled", "revoked"])
def test_rejects_inactive_trust_key(status: str) -> None:
    trusted = trust_store()
    trusted["keys"][0]["status"] = status

    with pytest.raises(DomainError) as error:
        _verify(sign_dossier(project_payload()), trusted)

    _assert_blocked(error)


@pytest.mark.policy
def test_rejects_expired_trust_key() -> None:
    trusted = trust_store()
    trusted["keys"][0]["expires_at"] = "2026-07-18T11:59:59Z"

    with pytest.raises(DomainError) as error:
        _verify(sign_dossier(project_payload()), trusted)

    _assert_blocked(error)


@pytest.mark.policy
def test_rejects_signer_kind_adapter_or_decision_outside_trust_grant() -> None:
    dossier = sign_dossier(project_payload())
    trusted = trust_store()
    trusted["keys"][0]["signer_kind"] = "operator"

    with pytest.raises(DomainError) as kind_error:
        _verify(dossier, trusted)

    _assert_blocked(kind_error)
    trusted = trust_store()
    trusted["keys"][0]["allowed_adapters"] = ["yt_dlp"]
    with pytest.raises(DomainError) as adapter_error:
        _verify(dossier, trusted)
    _assert_blocked(adapter_error)
    trusted = trust_store()
    trusted["keys"][0]["allowed_decisions"] = ["block"]
    with pytest.raises(DomainError) as decision_error:
        _verify(dossier, trusted)
    _assert_blocked(decision_error)


@pytest.mark.policy
def test_probe_permission_never_implies_download_permission() -> None:
    trusted = trust_store()
    trusted["keys"][0]["allowed_operations"] = ["probe", "download"]
    dossier = sign_dossier(project_payload())

    assert _verify(dossier, trusted, operation="probe")["decision"] == "allow"
    with pytest.raises(DomainError) as error:
        _verify(dossier, trusted, operation="download")

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.parametrize("official_url", [None, "http://www.w3.org/media"])
def test_open_official_requires_a_verified_https_url(official_url: str | None) -> None:
    payload = project_payload()
    if official_url is None:
        payload.pop("official_url")
    else:
        payload["official_url"] = official_url

    with pytest.raises(DomainError) as error:
        _verify(sign_dossier(payload), trust_store())

    _assert_blocked(error)


@pytest.mark.policy
def test_rejects_dossier_fields_not_allowed_by_frozen_schema() -> None:
    payload = project_payload()
    payload["cookie"] = "must-never-be-accepted"

    with pytest.raises(DomainError) as error:
        _verify(sign_dossier(payload), trust_store())

    _assert_blocked(error)


@pytest.mark.policy
def test_signature_cannot_be_replayed_under_another_key_id() -> None:
    dossier = deepcopy(sign_dossier(project_payload()))
    dossier["signature"]["key_id"] = PROJECT_KEY_ID + "-other"

    with pytest.raises(DomainError) as error:
        _verify(dossier, trust_store())

    _assert_blocked(error)
