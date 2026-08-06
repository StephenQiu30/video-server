from __future__ import annotations

import pytest
from app.runner.signing import (
    ExpiredSignatureError,
    HmacRequestAuthenticator,
    InMemoryNonceGuard,
    InvalidNonceError,
    InvalidSignatureError,
    ReplayDetectedError,
    sign_request,
)

SECRET = b"runner-shared-secret-material-32b"
NONCE = "a_nonce_value_123456"


def make_authenticator() -> HmacRequestAuthenticator:
    return HmacRequestAuthenticator(
        SECRET,
        nonce_guard=InMemoryNonceGuard(ttl_seconds=36, max_entries=100),
        max_age_seconds=30,
        max_future_skew_seconds=5,
    )


def test_replay_ttl_must_cover_the_signature_window() -> None:
    with pytest.raises(ValueError):
        HmacRequestAuthenticator(
            SECRET,
            nonce_guard=InMemoryNonceGuard(ttl_seconds=35, max_entries=100),
            max_age_seconds=30,
            max_future_skew_seconds=5,
        )


def test_valid_signature_is_accepted_once() -> None:
    auth = make_authenticator()
    signature = auth.sign("POST", "/runner/inspect", b'{"url":"x"}', 100, NONCE)

    auth.verify(
        "POST",
        "/runner/inspect",
        b'{"url":"x"}',
        timestamp=100,
        nonce=NONCE,
        signature=signature,
        now=105,
    )

    with pytest.raises(ReplayDetectedError):
        auth.verify(
            "POST",
            "/runner/inspect",
            b'{"url":"x"}',
            timestamp=100,
            nonce=NONCE,
            signature=signature,
            now=106,
        )


def test_stateless_signer_matches_authenticator_canonical_signature() -> None:
    auth = make_authenticator()

    expected = auth.sign("POST", "/runner/inspect", b"body", 100, NONCE)

    assert (
        sign_request(
            SECRET,
            "POST",
            "/runner/inspect",
            b"body",
            100,
            NONCE,
        )
        == expected
    )


def test_tampered_request_does_not_consume_nonce() -> None:
    auth = make_authenticator()
    signature = auth.sign("POST", "/runner/inspect", b"original", 100, NONCE)

    with pytest.raises(InvalidSignatureError):
        auth.verify(
            "POST",
            "/runner/inspect",
            b"tampered",
            100,
            NONCE,
            signature,
            now=100,
        )

    auth.verify(
        "POST",
        "/runner/inspect",
        b"original",
        100,
        NONCE,
        signature,
        now=100,
    )


@pytest.mark.parametrize("signature", ["not-hex", "\u00e9" * 64, "a" * 63])
def test_malformed_signature_is_rejected_without_consuming_nonce(
    signature: str,
) -> None:
    auth = make_authenticator()

    with pytest.raises(InvalidSignatureError):
        auth.verify(
            "POST",
            "/runner/inspect",
            b"body",
            100,
            NONCE,
            signature,
            now=100,
        )

    valid = auth.sign("POST", "/runner/inspect", b"body", 100, NONCE)
    auth.verify("POST", "/runner/inspect", b"body", 100, NONCE, valid, now=100)


@pytest.mark.parametrize(("timestamp", "now"), [(69, 100), (106, 100)])
def test_rejects_expired_or_excessively_future_timestamp(
    timestamp: int,
    now: int,
) -> None:
    auth = make_authenticator()
    signature = auth.sign("GET", "/runner/status", b"", timestamp, NONCE)

    with pytest.raises(ExpiredSignatureError):
        auth.verify(
            "GET",
            "/runner/status",
            b"",
            timestamp,
            NONCE,
            signature,
            now=now,
        )


@pytest.mark.parametrize("nonce", ["short", "contains space 123", "a" * 129])
def test_rejects_malformed_nonce(nonce: str) -> None:
    auth = make_authenticator()

    with pytest.raises(InvalidNonceError):
        auth.sign("GET", "/runner/status", b"", 100, nonce)


def test_nonce_may_be_claimed_again_only_after_ttl() -> None:
    guard = InMemoryNonceGuard(ttl_seconds=10, max_entries=2)

    guard.claim(NONCE, now=100)
    with pytest.raises(ReplayDetectedError):
        guard.claim(NONCE, now=109)

    guard.claim(NONCE, now=110)


def test_signature_binds_method_target_and_body() -> None:
    auth = make_authenticator()
    signature = auth.sign("POST", "/runner/inspect", b"body", 100, NONCE)

    for method, target, body in (
        ("PUT", "/runner/inspect", b"body"),
        ("POST", "/runner/download", b"body"),
        ("POST", "/runner/inspect", b"other"),
    ):
        with pytest.raises(InvalidSignatureError):
            auth.verify(
                method,
                target,
                body,
                100,
                NONCE,
                signature,
                now=100,
            )
