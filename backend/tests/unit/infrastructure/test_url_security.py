from __future__ import annotations

import pytest
from app.application.downloads import EncryptedUrl
from app.core.url_cipher import URLCipher
from app.infrastructure.url_security import FernetUrlEnvelope, MediaUrlValidator

KEY = b"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


def test_url_envelope_round_trip_binds_nonce_and_key() -> None:
    adapter = FernetUrlEnvelope(URLCipher(KEY), key_id="fernet-v1")
    source = "https://media.example/video?id=sensitive"

    encrypted = adapter.encrypt(source)

    assert source.encode() not in encrypted.ciphertext
    assert len(encrypted.nonce) == 16
    assert adapter.decrypt(encrypted) == source


def test_url_envelope_rejects_nonce_or_key_mismatch() -> None:
    adapter = FernetUrlEnvelope(URLCipher(KEY), key_id="fernet-v1")
    encrypted = adapter.encrypt("https://media.example/video")

    with pytest.raises(ValueError, match="nonce"):
        adapter.decrypt(
            EncryptedUrl(
                encrypted.ciphertext,
                b"x" * 16,
                encrypted.key_id,
            )
        )
    with pytest.raises(ValueError, match="key id"):
        adapter.decrypt(
            EncryptedUrl(
                encrypted.ciphertext,
                encrypted.nonce,
                "retired-key",
            )
        )


def test_media_url_validator_uses_runner_policy() -> None:
    validator = MediaUrlValidator()

    assert validator.validate("https://media.example/video") == (
        "https://media.example/video"
    )
    with pytest.raises(ValueError):
        validator.validate("http://127.0.0.1/video")
