from __future__ import annotations

import pytest
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
    open_cookie_lease,
    public_key_bytes,
    seal_cookie_lease,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

COOKIE = b"# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tx\n"


def test_successful_lease_is_encrypted_for_one_ephemeral_private_key() -> None:
    recipient = X25519PrivateKey.generate()
    request = b"youtube\nbrowser\npublic-key\n"

    response = seal_cookie_lease(
        ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
        public_key_bytes(recipient),
        associated_data=request,
    )

    assert COOKIE not in response
    assert open_cookie_lease(response, recipient, associated_data=request) == COOKIE


def test_lease_cannot_be_opened_by_another_operation_or_request() -> None:
    recipient = X25519PrivateKey.generate()
    response = seal_cookie_lease(
        ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
        public_key_bytes(recipient),
        associated_data=b"request-a",
    )

    for private_key, request in (
        (X25519PrivateKey.generate(), b"request-a"),
        (recipient, b"request-b"),
    ):
        with pytest.raises(RunnerFailure) as caught:
            open_cookie_lease(response, private_key, associated_data=request)
        assert caught.value.code == "provider_session_unavailable"


@pytest.mark.parametrize(
    ("status", "expected_code", "expected_status"),
    (
        (ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED, "credential_required", 422),
        (
            ProviderCookieLeaseStatus.SESSION_UNAVAILABLE,
            "provider_session_unavailable",
            503,
        ),
    ),
)
def test_non_secret_statuses_map_to_stable_runner_errors(
    status: ProviderCookieLeaseStatus,
    expected_code: str,
    expected_status: int,
) -> None:
    recipient = X25519PrivateKey.generate()
    response = seal_cookie_lease(
        ProviderCookieLease(status),
        public_key_bytes(recipient),
        associated_data=b"request",
    )

    with pytest.raises(RunnerFailure) as caught:
        open_cookie_lease(response, recipient, associated_data=b"request")
    assert caught.value.code == expected_code
    assert caught.value.status == expected_status
