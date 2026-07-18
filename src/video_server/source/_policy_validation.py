"""Fail-closed validation helpers for signed source-policy dossiers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from video_server.errors import DomainError
from video_server.source.urls import canonicalize_source_url

Scope = tuple[str, str, str]
_BLOCKED_MEDIA_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "youtube.googleapis.com",
    "googlevideo.com",
)


def blocked() -> DomainError:
    return DomainError(
        "SOURCE_POLICY_BLOCKED",
        "The source policy does not authorize this operation.",
        retryable=False,
    )


def as_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise blocked()
    return cast(Mapping[str, Any], value)


def as_string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise blocked()
    return tuple(value)


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise blocked()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise blocked() from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise blocked()
    return parsed


@cache
def _dossier_validator() -> Draft202012Validator:
    path = Path(__file__).resolve().parents[3] / "schemas" / "source-policy-dossier.schema.json"
    try:
        schema: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise blocked() from None
    if not isinstance(schema, Mapping):
        raise blocked()
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_dossier_schema(dossier: Mapping[str, Any]) -> None:
    if next(_dossier_validator().iter_errors(dossier), None) is not None:
        raise blocked()


def canonical_scope(value: Any) -> Scope:
    raw = as_mapping(value)
    origin = raw.get("origin")
    path_match = raw.get("path_match")
    path = raw.get("path")
    if not isinstance(origin, str) or path_match not in {"exact", "prefix"}:
        raise blocked()
    if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
        raise blocked()
    try:
        canonical_url = canonicalize_source_url(origin + path)
    except DomainError:
        raise blocked() from None
    parsed = urlsplit(canonical_url)
    canonical_origin = f"https://{parsed.netloc}"
    if origin != canonical_origin or path != parsed.path:
        raise blocked()
    if path_match == "prefix" and not path.endswith("/"):
        raise blocked()
    return canonical_origin, cast(str, path_match), path


def scope_list(value: Any) -> tuple[Scope, ...]:
    if not isinstance(value, list) or not value:
        raise blocked()
    scopes = tuple(canonical_scope(item) for item in value)
    if len(set(scopes)) != len(scopes):
        raise blocked()
    return scopes


def scope_matches(scope: Scope, origin: str, path: str) -> bool:
    scoped_origin, match, scoped_path = scope
    return scoped_origin == origin and (
        path == scoped_path if match == "exact" else path.startswith(scoped_path)
    )


def scope_contains(grant: Scope, candidate: Scope) -> bool:
    grant_origin, grant_match, grant_path = grant
    candidate_origin, candidate_match, candidate_path = candidate
    if grant_origin != candidate_origin:
        return False
    if grant_match == "exact":
        return candidate_match == "exact" and candidate_path == grant_path
    return candidate_path.startswith(grant_path)


def source_identity(source_url: str) -> tuple[str, str, str]:
    try:
        canonical = canonicalize_source_url(source_url)
    except DomainError:
        raise blocked() from None
    parsed = urlsplit(canonical)
    host = parsed.hostname
    if host is None or any(
        host == domain or host.endswith(f".{domain}") for domain in _BLOCKED_MEDIA_DOMAINS
    ):
        raise blocked()
    return f"https://{parsed.netloc}", parsed.path, host


def validate_egress(payload: Mapping[str, Any], scopes: tuple[Scope, ...]) -> None:
    hosts = as_string_list(payload.get("egress_hosts"))
    scope_hosts = {urlsplit(scope[0]).hostname for scope in scopes}
    if len(set(hosts)) != len(hosts) or set(hosts) != scope_hosts:
        raise blocked()
    for host in hosts:
        try:
            canonical = canonicalize_source_url(f"https://{host}/")
        except DomainError:
            raise blocked() from None
        if urlsplit(canonical).hostname != host:
            raise blocked()


def find_trust_key(trust_store: Mapping[str, Any], key_id: str) -> Mapping[str, Any]:
    if trust_store.get("schema_version") != "1.0":
        raise blocked()
    keys = trust_store.get("keys")
    if not isinstance(keys, list):
        raise blocked()
    matches = [as_mapping(key) for key in keys if as_mapping(key).get("key_id") == key_id]
    if len(matches) != 1:
        raise blocked()
    return matches[0]


def validate_operator_grant(
    key: Mapping[str, Any],
    payload: Mapping[str, Any],
    scopes: tuple[Scope, ...],
    *,
    issued_at: datetime,
    expires_at: datetime,
    now: datetime,
) -> None:
    grant = as_mapping(key.get("origin_grant"))
    grant_scope = canonical_scope(grant)
    verified_at = parse_time(grant.get("verified_at"))
    grant_expires = parse_time(grant.get("expires_at"))
    if (
        verified_at > now
        or now >= grant_expires
        or grant_expires > verified_at + timedelta(days=30)
        or issued_at < verified_at
        or expires_at > grant_expires
    ):
        raise blocked()
    if expires_at > issued_at + timedelta(days=30):
        raise blocked()
    if any(not scope_contains(grant_scope, scope) for scope in scopes):
        raise blocked()
    evidence = as_mapping(payload.get("evidence"))
    proof = evidence.get("origin_control_proof_sha256")
    if evidence.get("kind") != "origin_control" or proof != grant.get("proof_sha256"):
        raise blocked()
    evidence_url = evidence.get("url")
    expected_url = grant_scope[0] + "/.well-known/video-workbench-policy.json"
    if evidence_url != expected_url:
        raise blocked()
