"""Bind encrypted deployment sources to provider, revision and expiry."""

from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from app.services.provider_guest import GuestScope
from app.services.provider_types import ProviderKey


class ProviderSessionCipher:
    def __init__(self, key: str) -> None:
        self._cipher = Fernet(key.encode("ascii"))

    def encrypt_guest(
        self, scope: GuestScope, revision: int, valid_until: datetime, payload: bytes
    ) -> bytes:
        return self._cipher.encrypt(
            self._guest_binding(scope, revision, valid_until) + payload
        )

    def decrypt_guest(
        self, scope: GuestScope, revision: int, valid_until: datetime, ciphertext: bytes
    ) -> bytes:
        try:
            plaintext = self._cipher.decrypt(ciphertext)
        except InvalidToken:
            raise ValueError("invalid guest ciphertext") from None
        binding = self._guest_binding(scope, revision, valid_until)
        if not plaintext.startswith(binding):
            raise ValueError("guest scope binding mismatch")
        return plaintext[len(binding) :]

    @staticmethod
    def _guest_binding(
        scope: GuestScope, revision: int, valid_until: datetime
    ) -> bytes:
        if revision < 1 or valid_until.tzinfo is None:
            raise ValueError("invalid guest material binding")
        # Different domain from account sources even when the deployment reuses
        # its encryption key. Include all client/egress fields through the key.
        prefix = f"provider-guest:{scope.key}:{revision}:{valid_until.timestamp()}\n"
        return prefix.encode()

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
