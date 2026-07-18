from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace

import pytest

from video_server.job.idempotency import (
    IdempotencyDecision,
    ResolutionRequest,
    digest_idempotency_key,
    digest_resolution_request,
    resolve_existing,
)

HMAC_KEY = bytes.fromhex("11" * 32)
RAW_KEY = "resolve-20260718-0001"
REQUEST = ResolutionRequest(
    url="https://media.example/video",
    rights_confirmed=True,
    rights_statement_version="rights-2026-07-18.1",
    rights_statement_locale="zh-CN",
)


def test_idempotency_key_digest_is_hmac_sha256_of_the_exact_raw_key() -> None:
    expected = hmac.new(HMAC_KEY, RAW_KEY.encode(), hashlib.sha256).hexdigest()

    assert digest_idempotency_key(RAW_KEY, hmac_key=HMAC_KEY) == expected
    assert digest_idempotency_key(f"{RAW_KEY}x", hmac_key=HMAC_KEY) != expected


def test_request_digest_is_hmac_of_canonical_complete_request() -> None:
    canonical = json.dumps(
        {
            "rights_confirmed": True,
            "rights_statement_locale": "zh-CN",
            "rights_statement_version": "rights-2026-07-18.1",
            "url": "https://media.example/video",
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    expected = hmac.new(HMAC_KEY, canonical, hashlib.sha256).hexdigest()

    assert digest_resolution_request(REQUEST, hmac_key=HMAC_KEY) == expected


@pytest.mark.parametrize(
    "changed",
    [
        replace(REQUEST, url="https://media.example/other"),
        replace(REQUEST, rights_confirmed=False),
        replace(REQUEST, rights_statement_version="rights-2026-07-19.1"),
        replace(REQUEST, rights_statement_locale="en-US"),
    ],
)
def test_request_digest_covers_every_frozen_semantic_field(
    changed: ResolutionRequest,
) -> None:
    assert digest_resolution_request(changed, hmac_key=HMAC_KEY) != (
        digest_resolution_request(REQUEST, hmac_key=HMAC_KEY)
    )


def test_key_and_request_use_separate_digest_domains() -> None:
    key_digest = digest_idempotency_key(RAW_KEY, hmac_key=HMAC_KEY)
    request_digest = digest_resolution_request(REQUEST, hmac_key=HMAC_KEY)

    assert key_digest != request_digest
    assert digest_idempotency_key(RAW_KEY, hmac_key=b"\x22" * 32) != key_digest
    assert digest_resolution_request(REQUEST, hmac_key=b"\x22" * 32) != request_digest


def test_missing_record_creates_and_same_key_same_request_replays() -> None:
    incoming = digest_resolution_request(REQUEST, hmac_key=HMAC_KEY)

    assert resolve_existing(None, incoming) is IdempotencyDecision.CREATE
    assert resolve_existing(incoming, incoming) is IdempotencyDecision.REPLAY


def test_same_key_with_different_request_is_a_conflict() -> None:
    stored = digest_resolution_request(REQUEST, hmac_key=HMAC_KEY)
    incoming = digest_resolution_request(
        replace(REQUEST, url="https://media.example/different"),
        hmac_key=HMAC_KEY,
    )

    assert resolve_existing(stored, incoming) is IdempotencyDecision.CONFLICT
