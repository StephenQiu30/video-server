"""Signed source-policy dossier verification boundary."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any

import rfc8785
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from video_server.errors import DomainError
from video_server.source._policy_validation import (
    as_mapping,
    as_string_list,
    blocked,
    find_trust_key,
    parse_time,
    scope_contains,
    scope_list,
    scope_matches,
    source_identity,
    validate_dossier_schema,
    validate_egress,
    validate_operator_grant,
)
from video_server.source.urls import canonicalize_source_url


def canonical_policy_payload(payload: Mapping[str, Any]) -> bytes:
    """Encode the signed payload as RFC 8785 JCS bytes."""

    try:
        return rfc8785.dumps(dict(payload))
    except (TypeError, ValueError):
        raise blocked() from None


def _decode_base64(value: Any, *, size: int) -> bytes:
    if not isinstance(value, str):
        raise blocked()
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise blocked() from None
    if len(decoded) != size or base64.b64encode(decoded).decode("ascii") != value:
        raise blocked()
    return decoded


def _validate_unique_public_keys(trust_store: Mapping[str, Any]) -> None:
    keys = trust_store.get("keys")
    if not isinstance(keys, list):
        raise blocked()
    public_keys = [_decode_base64(as_mapping(key).get("public_key"), size=32) for key in keys]
    if len(public_keys) != len(set(public_keys)):
        raise blocked()


def _validate_https_url(value: Any) -> None:
    if not isinstance(value, str):
        raise blocked()
    try:
        canonicalize_source_url(value)
    except DomainError:
        raise blocked() from None


def _validate_context(
    payload: Mapping[str, Any],
    key: Mapping[str, Any],
    *,
    operation: str,
    source_url: str,
    now: datetime,
) -> None:
    if now.tzinfo is None or now.utcoffset() is None or operation != "probe":
        raise blocked()
    issued_at = parse_time(payload.get("issued_at"))
    expires_at = parse_time(payload.get("expires_at"))
    if issued_at > now or now >= expires_at or expires_at <= issued_at:
        raise blocked()

    if key.get("status") != "active" or key.get("signer_kind") != payload.get("signer_kind"):
        raise blocked()
    key_not_before = parse_time(key.get("not_before"))
    key_expires = parse_time(key.get("expires_at"))
    if key_not_before > now or now >= key_expires:
        raise blocked()
    if issued_at < key_not_before or expires_at > key_expires:
        raise blocked()

    decisions = as_string_list(key.get("allowed_decisions"))
    adapters = as_string_list(key.get("allowed_adapters"))
    trusted_operations = as_string_list(key.get("allowed_operations"))
    permitted_operations = as_string_list(payload.get("permitted_operations"))
    if payload.get("decision") != "allow" or payload.get("decision") not in decisions:
        raise blocked()
    if payload.get("adapter") not in adapters:
        raise blocked()
    if operation not in trusted_operations or operation not in permitted_operations:
        raise blocked()

    scopes = scope_list(payload.get("scope"))
    trusted_scopes = scope_list(key.get("scope"))
    if any(not any(scope_contains(grant, scope) for grant in trusted_scopes) for scope in scopes):
        raise blocked()
    origin, path, source_host = source_identity(source_url)
    if not any(scope_matches(scope, origin, path) for scope in scopes):
        raise blocked()
    if not any(scope_matches(scope, origin, path) for scope in trusted_scopes):
        raise blocked()
    validate_egress(payload, scopes)
    if source_host not in as_string_list(payload.get("egress_hosts")):
        raise blocked()

    actions = as_string_list(payload.get("user_actions"))
    official_url = payload.get("official_url")
    if "open_official" in actions or official_url is not None:
        _validate_https_url(official_url)
    evidence = as_mapping(payload.get("evidence"))
    _validate_https_url(evidence.get("url"))
    if parse_time(evidence.get("reviewed_at")) > now:
        raise blocked()

    if payload.get("signer_kind") == "operator":
        validate_operator_grant(
            key,
            payload,
            scopes,
            issued_at=issued_at,
            expires_at=expires_at,
            now=now,
        )
    elif evidence.get("kind") != "public_documentation":
        raise blocked()


def verify_policy_dossier(
    dossier: Mapping[str, Any],
    trust_store: Mapping[str, Any],
    *,
    operation: str,
    source_url: str,
    now: datetime,
) -> Mapping[str, Any]:
    """Verify signature, trust grant, lifecycle, scope, and operation."""

    try:
        validate_dossier_schema(dossier)
        payload = as_mapping(dossier.get("payload"))
        signature = as_mapping(dossier.get("signature"))
        key_id = signature.get("key_id")
        if not isinstance(key_id, str):
            raise blocked()
        _validate_unique_public_keys(trust_store)
        key = find_trust_key(trust_store, key_id)
        public_key = _decode_base64(key.get("public_key"), size=32)
        signature_bytes = _decode_base64(signature.get("value"), size=64)
        VerifyKey(public_key).verify(canonical_policy_payload(payload), signature_bytes)
        _validate_context(
            payload,
            key,
            operation=operation,
            source_url=source_url,
            now=now,
        )
        return deepcopy(dict(payload))
    except DomainError as error:
        if error.code == "SOURCE_POLICY_BLOCKED":
            raise
        raise blocked() from None
    except (BadSignatureError, TypeError, ValueError):
        raise blocked() from None
