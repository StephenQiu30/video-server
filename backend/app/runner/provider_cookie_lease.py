"""One-operation encrypted transport for provider browser sessions."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.runner.errors import RunnerFailure


class ProviderCookieLeaseStatus(StrEnum):
    OK = "ok"
    CREDENTIAL_REQUIRED = "credential_required"
    SESSION_UNAVAILABLE = "provider_session_unavailable"


@dataclass(frozen=True, slots=True)
class ProviderCookieLease:
    status: ProviderCookieLeaseStatus
    payload: bytes | None = None

    def __post_init__(self) -> None:
        if (self.status is ProviderCookieLeaseStatus.OK) != (self.payload is not None):
            raise ValueError("provider Cookie lease payload does not match status")


PUBLIC_KEY_BYTES: Final = 32
NONCE_BYTES: Final = 12
MAX_COOKIE_BYTES: Final = 1024**2
MAX_RESPONSE_BYTES: Final = MAX_COOKIE_BYTES + 256
_SUCCESS_PREFIX: Final = b"ok\n"
_INFO: Final = b"framefetch-provider-cookie-lease"


def public_key_bytes(private_key: X25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def encode_public_key(value: bytes) -> str:
    if len(value) != PUBLIC_KEY_BYTES:
        raise ValueError("invalid provider Cookie lease public key")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode_public_key(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value + "=", altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("invalid provider Cookie lease public key") from exc
    if len(decoded) != PUBLIC_KEY_BYTES:
        raise ValueError("invalid provider Cookie lease public key")
    return decoded


def seal_cookie_lease(
    lease: ProviderCookieLease,
    recipient_public_key: bytes,
    *,
    associated_data: bytes,
    private_key: X25519PrivateKey | None = None,
    nonce: bytes | None = None,
) -> bytes:
    if lease.status is not ProviderCookieLeaseStatus.OK:
        return lease.status.value.encode("ascii")
    assert lease.payload is not None
    if not 0 < len(lease.payload) <= MAX_COOKIE_BYTES:
        raise ValueError("provider Cookie lease exceeds the size limit")
    ephemeral = private_key or X25519PrivateKey.generate()
    peer = X25519PublicKey.from_public_bytes(recipient_public_key)
    active_nonce = nonce or os.urandom(NONCE_BYTES)
    if len(active_nonce) != NONCE_BYTES:
        raise ValueError("invalid provider Cookie lease nonce")
    ciphertext = ChaCha20Poly1305(_lease_key(ephemeral.exchange(peer))).encrypt(
        active_nonce,
        lease.payload,
        associated_data,
    )
    response = _SUCCESS_PREFIX + public_key_bytes(ephemeral) + active_nonce + ciphertext
    if len(response) > MAX_RESPONSE_BYTES:
        raise ValueError("provider Cookie lease exceeds the response limit")
    return response


def open_cookie_lease(
    response: bytes,
    private_key: X25519PrivateKey,
    *,
    associated_data: bytes,
) -> bytes:
    if not response.startswith(_SUCCESS_PREFIX):
        try:
            status = ProviderCookieLeaseStatus(response.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RunnerFailure("provider_session_unavailable", status=503) from exc
        if status is ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED:
            raise RunnerFailure("credential_required", status=422)
        raise RunnerFailure("provider_session_unavailable", status=503)
    offset = len(_SUCCESS_PREFIX)
    minimum = offset + PUBLIC_KEY_BYTES + NONCE_BYTES + 16
    if len(response) < minimum or len(response) > MAX_RESPONSE_BYTES:
        raise RunnerFailure("provider_session_unavailable", status=503)
    peer_bytes = response[offset : offset + PUBLIC_KEY_BYTES]
    nonce_offset = offset + PUBLIC_KEY_BYTES
    nonce = response[nonce_offset : nonce_offset + NONCE_BYTES]
    ciphertext = response[nonce_offset + NONCE_BYTES :]
    try:
        peer = X25519PublicKey.from_public_bytes(peer_bytes)
        payload = ChaCha20Poly1305(_lease_key(private_key.exchange(peer))).decrypt(
            nonce,
            ciphertext,
            associated_data,
        )
    except Exception as exc:
        raise RunnerFailure("provider_session_unavailable", status=503) from exc
    if not 0 < len(payload) <= MAX_COOKIE_BYTES:
        raise RunnerFailure("provider_session_unavailable", status=503)
    return payload


def serialize_export(lease: ProviderCookieLease) -> bytes:
    if lease.status is not ProviderCookieLeaseStatus.OK:
        return lease.status.value.encode("ascii")
    assert lease.payload is not None
    if not 0 < len(lease.payload) <= MAX_COOKIE_BYTES:
        raise ValueError("provider Cookie export exceeds the size limit")
    return _SUCCESS_PREFIX + lease.payload


def parse_export(payload: bytes) -> ProviderCookieLease:
    if payload.startswith(_SUCCESS_PREFIX):
        cookie_payload = payload[len(_SUCCESS_PREFIX) :]
        if not 0 < len(cookie_payload) <= MAX_COOKIE_BYTES:
            return ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, cookie_payload)
    try:
        status = ProviderCookieLeaseStatus(payload.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        status = ProviderCookieLeaseStatus.SESSION_UNAVAILABLE
    if status is ProviderCookieLeaseStatus.OK:
        status = ProviderCookieLeaseStatus.SESSION_UNAVAILABLE
    return ProviderCookieLease(status)


def _lease_key(shared_secret: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_INFO,
    ).derive(shared_secret)
