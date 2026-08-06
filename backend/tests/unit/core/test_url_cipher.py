from __future__ import annotations

import pytest
from app.core.url_cipher import URLCipher
from cryptography.fernet import InvalidToken

KEY = b"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


def test_url_cipher_round_trip_without_plaintext_leak() -> None:
    cipher = URLCipher(KEY)
    url = "https://media.example/video?id=private-token"

    encrypted = cipher.encrypt(url)

    assert url not in encrypted.decode()
    assert cipher.decrypt(encrypted) == url


def test_url_cipher_rejects_tampered_ciphertext() -> None:
    cipher = URLCipher(KEY)
    encrypted = cipher.encrypt("https://media.example/video")
    tampered = bytearray(encrypted)
    tampered[-10] ^= 1

    with pytest.raises(InvalidToken):
        cipher.decrypt(bytes(tampered))
