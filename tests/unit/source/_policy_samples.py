from __future__ import annotations

import base64
from copy import deepcopy
from typing import Any

import rfc8785
from nacl.signing import SigningKey

PROJECT_KEY_ID = "project-test-1"
OPERATOR_KEY_ID = "operator-test-1"
PROJECT_SEED = bytes(range(32))
OPERATOR_SEED = bytes(reversed(range(32)))
PROOF_HASH = "8" * 64


def project_payload() -> dict[str, Any]:
    return {
        "policy_id": "w3c-sintel",
        "name": "W3C Sintel",
        "revision": 1,
        "signer_kind": "project",
        "decision": "allow",
        "permitted_operations": ["probe"],
        "adapter": "direct_http",
        "scope": [
            {
                "origin": "https://media.w3.org",
                "path_match": "exact",
                "path": "/2010/05/sintel/trailer.mp4",
            }
        ],
        "egress_hosts": ["media.w3.org"],
        "user_actions": ["view_supported_sources", "open_official"],
        "official_url": "https://www.w3.org/2010/05/video/mediaevents.html",
        "detectors": {
            "reject_auth": True,
            "reject_disabled_download": True,
            "reject_drm": True,
        },
        "evidence": {
            "kind": "public_documentation",
            "url": "https://www.w3.org/2010/05/video/mediaevents.html",
            "sha256": "4" * 64,
            "reviewed_at": "2026-07-18T00:00:00Z",
        },
        "issued_at": "2026-07-18T00:00:00Z",
        "expires_at": "2026-07-28T00:00:00Z",
    }


def operator_payload() -> dict[str, Any]:
    payload = project_payload()
    payload.update(
        {
            "policy_id": "owned-media",
            "name": "Owned media",
            "signer_kind": "operator",
            "scope": [
                {
                    "origin": "https://owned.example",
                    "path_match": "prefix",
                    "path": "/videos/",
                }
            ],
            "egress_hosts": ["owned.example"],
            "official_url": "https://owned.example/about",
            "evidence": {
                "kind": "origin_control",
                "url": "https://owned.example/.well-known/video-workbench-policy.json",
                "sha256": "7" * 64,
                "reviewed_at": "2026-07-18T00:00:00Z",
                "origin_control_proof_sha256": PROOF_HASH,
            },
        }
    )
    return payload


def sign_dossier(
    payload: dict[str, Any],
    *,
    key_id: str = PROJECT_KEY_ID,
    seed: bytes = PROJECT_SEED,
) -> dict[str, Any]:
    message = rfc8785.dumps(payload)
    signature = SigningKey(seed).sign(message).signature
    return {
        "schema_version": "1.0",
        "payload": deepcopy(payload),
        "signature": {
            "key_id": key_id,
            "algorithm": "Ed25519",
            "value": base64.b64encode(signature).decode("ascii"),
        },
    }


def trust_store(*, operator: bool = False) -> dict[str, Any]:
    seed = OPERATOR_SEED if operator else PROJECT_SEED
    key_id = OPERATOR_KEY_ID if operator else PROJECT_KEY_ID
    signer_kind = "operator" if operator else "project"
    scope = operator_payload()["scope"] if operator else project_payload()["scope"]
    key: dict[str, Any] = {
        "key_id": key_id,
        "public_key": base64.b64encode(bytes(SigningKey(seed).verify_key)).decode("ascii"),
        "status": "active",
        "signer_kind": signer_kind,
        "allowed_decisions": ["allow"],
        "allowed_adapters": ["direct_http"],
        "allowed_operations": ["probe"],
        "scope": deepcopy(scope),
        "not_before": "2026-07-17T00:00:00Z",
        "expires_at": "2026-08-01T00:00:00Z",
    }
    if operator:
        key["origin_grant"] = {
            "origin": "https://owned.example",
            "path_match": "prefix",
            "path": "/videos/",
            "proof_sha256": PROOF_HASH,
            "verified_at": "2026-07-18T00:00:00Z",
            "expires_at": "2026-07-30T00:00:00Z",
        }
    return {"schema_version": "1.0", "keys": [key]}
