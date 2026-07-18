"""XChaCha20-Poly1305 row-envelope encryption boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EncryptedEnvelope:
    ciphertext: bytes
    nonce: bytes
    wrapped_dek: bytes
    wrap_nonce: bytes
    key_id: str


class EnvelopeCipher:
    """Encrypt row payloads with random DEKs wrapped by a versioned KEK."""

    def __init__(self, keyring: Mapping[str, bytes], *, current_key_id: str) -> None:
        raise NotImplementedError("envelope cipher construction is not implemented")

    @property
    def current_key_id(self) -> str:
        raise NotImplementedError("current key lookup is not implemented")

    def encrypt(self, plaintext: bytes, *, aad: bytes) -> EncryptedEnvelope:
        raise NotImplementedError("envelope encryption is not implemented")

    def decrypt(self, envelope: EncryptedEnvelope, *, aad: bytes) -> bytes:
        raise NotImplementedError("envelope decryption is not implemented")

    def rewrap(
        self,
        envelope: EncryptedEnvelope,
        *,
        aad: bytes,
        new_key_id: str,
    ) -> EncryptedEnvelope:
        raise NotImplementedError("envelope rewrap is not implemented")
