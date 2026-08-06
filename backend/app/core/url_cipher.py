"""Encryption boundary for user-supplied source URLs."""

from cryptography.fernet import Fernet


class URLCipher:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, url: str) -> bytes:
        return self._fernet.encrypt(url.encode())

    def decrypt(self, encrypted: bytes) -> str:
        return self._fernet.decrypt(encrypted).decode()
