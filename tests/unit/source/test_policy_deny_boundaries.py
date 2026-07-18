from __future__ import annotations

import base64
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from tests.unit.source._policy_samples import project_payload, sign_dossier, trust_store
from video_server.errors import DomainError
from video_server.source.policies import verify_policy_dossier

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
SOURCE_PATH = "/video.mp4"
BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _assert_blocked(error: pytest.ExceptionInfo[DomainError]) -> None:
    assert error.value.code == "SOURCE_POLICY_BLOCKED"


@pytest.mark.policy
@pytest.mark.security
@pytest.mark.parametrize(
    "host",
    [
        "www.youtube-nocookie.com",
        "youtube.googleapis.com",
        "rr1.googlevideo.com",
    ],
)
def test_youtube_owned_alternate_hosts_are_blocked_before_extractor(host: str) -> None:
    payload = project_payload()
    payload["policy_id"] = "youtube-alternate-host"
    payload["scope"] = [{"origin": f"https://{host}", "path_match": "exact", "path": SOURCE_PATH}]
    payload["egress_hosts"] = [host]
    trusted = trust_store()
    trusted["keys"][0]["scope"] = deepcopy(payload["scope"])

    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            sign_dossier(payload),
            trusted,
            operation="probe",
            source_url=f"https://{host}{SOURCE_PATH}",
            now=NOW,
        )

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.security
def test_noncanonical_base64_signature_encoding_is_rejected() -> None:
    dossier = sign_dossier(project_payload())
    canonical = dossier["signature"]["value"]
    significant_index = BASE64_ALPHABET.index(canonical[-3])
    replacement_index = (significant_index & 0b110000) | ((significant_index + 1) & 0b001111)
    noncanonical = canonical[:-3] + BASE64_ALPHABET[replacement_index] + "=="
    assert noncanonical != canonical
    assert base64.b64decode(noncanonical) == base64.b64decode(canonical)
    dossier["signature"]["value"] = noncanonical

    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            dossier,
            trust_store(),
            operation="probe",
            source_url="https://media.w3.org/2010/05/sintel/trailer.mp4",
            now=NOW,
        )

    _assert_blocked(error)


@pytest.mark.policy
@pytest.mark.security
def test_active_key_alias_cannot_bypass_revoked_identical_public_key() -> None:
    dossier = sign_dossier(project_payload())
    trusted = trust_store()
    revoked = trusted["keys"][0]
    revoked["status"] = "revoked"
    active_alias = deepcopy(revoked)
    active_alias["key_id"] = "project-test-alias"
    active_alias["status"] = "active"
    trusted["keys"].append(active_alias)
    dossier["signature"]["key_id"] = active_alias["key_id"]

    with pytest.raises(DomainError) as error:
        verify_policy_dossier(
            dossier,
            trusted,
            operation="probe",
            source_url="https://media.w3.org/2010/05/sintel/trailer.mp4",
            now=NOW,
        )

    _assert_blocked(error)
