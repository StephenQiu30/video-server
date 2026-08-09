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


def test_media_url_validator_extracts_scheme_less_xhs_share_link() -> None:
    validator = MediaUrlValidator()

    assert (
        validator.validate("复制后打开小红书 xhslink.com/m/AbC123 更多内容。")
        == "https://xhslink.com/m/AbC123"
    )
    assert validator.validate("https://xhslink.com/a/AbC123?source=copy") == (
        "https://xhslink.com/a/AbC123?source=copy"
    )


def test_media_url_validator_extracts_douyin_url_from_share_message() -> None:
    validator = MediaUrlValidator()
    message = (
        "9.25 04/21 :1pm F@U.yt Bgb:/ ୨୧⊹ ࣪ 幸福是一步步变成小蛋糕 "
        "https://v.douyin.com/Tq0eYJRMYRk/ 复制此链接，打开Dou音搜索"
    )

    assert validator.validate(message) == "https://v.douyin.com/Tq0eYJRMYRk/"


def test_media_url_validator_rejects_share_message_with_multiple_urls() -> None:
    validator = MediaUrlValidator()

    with pytest.raises(ValueError):
        validator.validate("https://v.douyin.com/first/ https://v.douyin.com/second/")


def test_media_url_validator_does_not_generalize_scheme_less_input() -> None:
    validator = MediaUrlValidator()

    with pytest.raises(ValueError):
        validator.validate("media.example/video")
    with pytest.raises(ValueError):
        validator.validate("xhslink.com/m/first xhslink.com/m/second")
