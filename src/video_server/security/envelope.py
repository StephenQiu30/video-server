"""XChaCha20-Poly1305 row-envelope encryption boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from nacl.bindings import (
    crypto_aead_xchacha20poly1305_ietf_ABYTES,
    crypto_aead_xchacha20poly1305_ietf_decrypt,
    crypto_aead_xchacha20poly1305_ietf_encrypt,
    crypto_aead_xchacha20poly1305_ietf_KEYBYTES,
    crypto_aead_xchacha20poly1305_ietf_NPUBBYTES,
    randombytes,
)
from nacl.exceptions import CryptoError

_DATA_AAD_DOMAIN = b"video-server:envelope:data:v1"
_WRAP_AAD_DOMAIN = b"video-server:envelope:wrap:v1"
_AUTHENTICATION_FAILURE = "envelope authentication failed"


@dataclass(frozen=True, slots=True)
class EncryptedEnvelope:
    ciphertext: bytes
    nonce: bytes
    wrapped_dek: bytes
    wrap_nonce: bytes
    key_id: str


class EnvelopeCipher:
    """Encrypt row payloads with random DEKs wrapped by a versioned KEK."""

    __slots__ = ("_current_key_id", "_keyring")

    def __init__(self, keyring: Mapping[str, bytes], *, current_key_id: str) -> None:
        if not isinstance(keyring, Mapping) or not keyring:
            raise ValueError("keyring must contain at least one KEK")
        if not _is_key_id(current_key_id):
            raise ValueError("current key id must be a non-empty string")

        copied: dict[str, bytes] = {}
        for key_id, key in keyring.items():
            if not _is_key_id(key_id):
                raise ValueError("key ids must be non-empty strings")
            if type(key) is not bytes or len(key) != crypto_aead_xchacha20poly1305_ietf_KEYBYTES:
                raise ValueError("each KEK must be exactly 32 bytes")
            copied[key_id] = key
        if current_key_id not in copied:
            raise ValueError("current key id is not present in the keyring")

        self._keyring = copied
        self._current_key_id = current_key_id

    @property
    def current_key_id(self) -> str:
        return self._current_key_id

    def encrypt(self, plaintext: bytes, *, aad: bytes) -> EncryptedEnvelope:
        plaintext = _nonempty_bytes(plaintext, name="plaintext")
        aad = _nonempty_bytes(aad, name="aad")
        dek = randombytes(crypto_aead_xchacha20poly1305_ietf_KEYBYTES)
        nonce = randombytes(crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
        wrap_nonce = randombytes(crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
        key_id = self._current_key_id

        ciphertext = crypto_aead_xchacha20poly1305_ietf_encrypt(
            plaintext,
            _data_aad(aad),
            nonce,
            dek,
        )
        wrapped_dek = crypto_aead_xchacha20poly1305_ietf_encrypt(
            dek,
            _wrap_aad(aad, key_id),
            wrap_nonce,
            self._keyring[key_id],
        )
        return EncryptedEnvelope(ciphertext, nonce, wrapped_dek, wrap_nonce, key_id)

    def decrypt(self, envelope: EncryptedEnvelope, *, aad: bytes) -> bytes:
        aad = _nonempty_bytes(aad, name="aad")
        envelope = _validated_envelope(envelope)
        dek = self._unwrap_dek(envelope, aad=aad)
        try:
            return crypto_aead_xchacha20poly1305_ietf_decrypt(
                envelope.ciphertext,
                _data_aad(aad),
                envelope.nonce,
                dek,
            )
        except (CryptoError, TypeError, ValueError):
            raise ValueError(_AUTHENTICATION_FAILURE) from None

    def rewrap(
        self,
        envelope: EncryptedEnvelope,
        *,
        aad: bytes,
        new_key_id: str,
    ) -> EncryptedEnvelope:
        aad = _nonempty_bytes(aad, name="aad")
        envelope = _validated_envelope(envelope)
        if not _is_key_id(new_key_id) or new_key_id not in self._keyring:
            raise ValueError(_AUTHENTICATION_FAILURE)

        dek = self._unwrap_dek(envelope, aad=aad)
        wrap_nonce = randombytes(crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
        wrapped_dek = crypto_aead_xchacha20poly1305_ietf_encrypt(
            dek,
            _wrap_aad(aad, new_key_id),
            wrap_nonce,
            self._keyring[new_key_id],
        )
        return EncryptedEnvelope(
            envelope.ciphertext,
            envelope.nonce,
            wrapped_dek,
            wrap_nonce,
            new_key_id,
        )

    def _unwrap_dek(self, envelope: EncryptedEnvelope, *, aad: bytes) -> bytes:
        try:
            key = self._keyring[envelope.key_id]
            return crypto_aead_xchacha20poly1305_ietf_decrypt(
                envelope.wrapped_dek,
                _wrap_aad(aad, envelope.key_id),
                envelope.wrap_nonce,
                key,
            )
        except (CryptoError, KeyError, TypeError, ValueError):
            raise ValueError(_AUTHENTICATION_FAILURE) from None


def _nonempty_bytes(value: object, *, name: str) -> bytes:
    if type(value) is not bytes or not value:
        raise ValueError(f"{name} must be non-empty bytes")
    return value


def _is_key_id(value: object) -> bool:
    if type(value) is not str or not value.strip():
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _validated_envelope(envelope: object) -> EncryptedEnvelope:
    if not isinstance(envelope, EncryptedEnvelope):
        raise ValueError(_AUTHENTICATION_FAILURE)
    valid = (
        type(envelope.ciphertext) is bytes
        and len(envelope.ciphertext) > crypto_aead_xchacha20poly1305_ietf_ABYTES
        and type(envelope.nonce) is bytes
        and len(envelope.nonce) == crypto_aead_xchacha20poly1305_ietf_NPUBBYTES
        and type(envelope.wrapped_dek) is bytes
        and len(envelope.wrapped_dek)
        == crypto_aead_xchacha20poly1305_ietf_KEYBYTES + crypto_aead_xchacha20poly1305_ietf_ABYTES
        and type(envelope.wrap_nonce) is bytes
        and len(envelope.wrap_nonce) == crypto_aead_xchacha20poly1305_ietf_NPUBBYTES
        and _is_key_id(envelope.key_id)
    )
    if not valid:
        raise ValueError(_AUTHENTICATION_FAILURE)
    return envelope


def _frame(value: bytes) -> bytes:
    return len(value).to_bytes(8, "big") + value


def _data_aad(aad: bytes) -> bytes:
    return _DATA_AAD_DOMAIN + _frame(aad)


def _wrap_aad(aad: bytes, key_id: str) -> bytes:
    return _WRAP_AAD_DOMAIN + _frame(key_id.encode("utf-8")) + _frame(aad)
