"""Bind encrypted deployment sources to provider, revision and expiry."""

from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from app.services.provider_types import ProviderKey


class ProviderSessionCipher:
    def __init__(self, key: str) -> None:
        self._cipher = Fernet(key.encode("ascii"))

    @staticmethod
    def _binding(provider: ProviderKey, revision: int, valid_until: datetime) -> bytes:
        expiry = int(valid_until.timestamp())
        return f"provider-source:{provider.value}:{revision}:{expiry}\n".encode()

    def encrypt(
        self,
        provider: ProviderKey,
        revision: int,
        valid_until: datetime,
        payload: bytes,
    ) -> bytes:
        return self._cipher.encrypt(
            self._binding(provider, revision, valid_until) + payload
        )

    def decrypt(
        self,
        provider: ProviderKey,
        revision: int,
        valid_until: datetime,
        ciphertext: bytes,
    ) -> bytes:
        try:
            plaintext = self._cipher.decrypt(ciphertext)
        except InvalidToken:
            raise ValueError("invalid provider source ciphertext") from None
        binding = self._binding(provider, revision, valid_until)
        if not plaintext.startswith(binding):
            raise ValueError("provider source binding mismatch")
        return plaintext[len(binding) :]
