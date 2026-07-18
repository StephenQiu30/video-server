from __future__ import annotations

from dataclasses import fields, replace
from typing import Any

import pytest

from video_server.security.envelope import EncryptedEnvelope, EnvelopeCipher

pytestmark = pytest.mark.security

OLD_KEY = b"\x11" * 32
NEW_KEY = b"\x22" * 32
WRONG_KEY = b"\x33" * 32
PLAINTEXT = b"private source url: https://media.example/video?id=secret"
AAD = b"source_resolution_requests:req-1:owner-1:url:v1"


def _runtime(value: object) -> Any:
    return value


def _flip(value: bytes) -> bytes:
    return bytes([value[0] ^ 1]) + value[1:]


def _assert_safe_failure(cipher: EnvelopeCipher, envelope: EncryptedEnvelope, aad: Any) -> None:
    with pytest.raises(ValueError) as caught:
        cipher.decrypt(envelope, aad=aad)

    failure = repr(caught.value)
    assert PLAINTEXT.decode() not in failure
    assert PLAINTEXT.hex() not in failure


@pytest.mark.parametrize(
    ("keyring", "current_key_id"),
    [
        ({}, "old"),
        ({"old": OLD_KEY}, ""),
        ({"old": OLD_KEY}, "   "),
        ({"": OLD_KEY, "old": NEW_KEY}, "old"),
        ({"   ": OLD_KEY, "old": NEW_KEY}, "old"),
        ({"old": OLD_KEY}, "missing"),
    ],
)
def test_keyring_requires_nonempty_ids_and_a_present_current_key(
    keyring: dict[str, bytes], current_key_id: str
) -> None:
    with pytest.raises(ValueError):
        EnvelopeCipher(keyring, current_key_id=current_key_id)


@pytest.mark.parametrize(
    "invalid_key",
    [
        b"",
        b"\x11" * 16,
        b"\x11" * 31,
        b"\x11" * 33,
        b"\x11" * 64,
        _runtime(bytearray(b"\x11" * 32)),
        _runtime(memoryview(b"\x11" * 32)),
        _runtime("1" * 32),
    ],
)
def test_keks_are_exactly_32_byte_bytes_not_other_purpose_secrets(
    invalid_key: Any,
) -> None:
    with pytest.raises(ValueError):
        EnvelopeCipher({"old": invalid_key}, current_key_id="old")


def test_cipher_exposes_only_the_selected_key_identifier() -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY, "new": NEW_KEY}, current_key_id="old")

    assert cipher.current_key_id == "old"


@pytest.mark.parametrize("plaintext", [b"", _runtime("secret"), _runtime(bytearray(b"x"))])
@pytest.mark.parametrize("aad", [AAD, b"", _runtime("aad"), _runtime(bytearray(b"aad"))])
def test_encrypt_requires_nonempty_bytes(plaintext: Any, aad: Any) -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY}, current_key_id="old")

    if isinstance(plaintext, bytes) and plaintext and isinstance(aad, bytes) and aad:
        pytest.skip("the valid pair is exercised by round-trip tests")
    with pytest.raises(ValueError):
        cipher.encrypt(plaintext, aad=aad)


def test_encrypt_uses_fresh_dek_and_nonces_and_authenticates_ciphertext() -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY}, current_key_id="old")

    first = cipher.encrypt(PLAINTEXT, aad=AAD)
    second = cipher.encrypt(PLAINTEXT, aad=AAD)

    assert first.key_id == second.key_id == "old"
    assert len(first.nonce) == len(first.wrap_nonce) == 24
    assert len(first.ciphertext) == len(PLAINTEXT) + 16
    assert len(first.wrapped_dek) == 32 + 16
    assert first.nonce != second.nonce
    assert first.wrap_nonce != second.wrap_nonce
    assert first.ciphertext != second.ciphertext
    assert first.wrapped_dek != second.wrapped_dek
    assert PLAINTEXT not in first.ciphertext
    assert cipher.decrypt(first, aad=AAD) == PLAINTEXT
    assert cipher.decrypt(second, aad=AAD) == PLAINTEXT


@pytest.mark.parametrize("bad_aad", [b"", b"wrong-aad", _runtime("not-bytes")])
def test_decrypt_rejects_empty_wrong_or_nonbyte_aad(bad_aad: Any) -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY}, current_key_id="old")
    envelope = cipher.encrypt(PLAINTEXT, aad=AAD)

    _assert_safe_failure(cipher, envelope, bad_aad)


def test_decrypt_safely_rejects_all_authenticated_component_tampering() -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY, "new": NEW_KEY}, current_key_id="old")
    envelope = cipher.encrypt(PLAINTEXT, aad=AAD)
    tampered = [
        replace(envelope, nonce=_flip(envelope.nonce)),
        replace(envelope, nonce=envelope.nonce[:-1]),
        replace(envelope, ciphertext=_flip(envelope.ciphertext)),
        replace(envelope, ciphertext=envelope.ciphertext[:-1]),
        replace(envelope, wrap_nonce=_flip(envelope.wrap_nonce)),
        replace(envelope, wrap_nonce=envelope.wrap_nonce[:-1]),
        replace(envelope, wrapped_dek=_flip(envelope.wrapped_dek)),
        replace(envelope, wrapped_dek=envelope.wrapped_dek[:-1]),
        replace(envelope, key_id="new"),
        replace(envelope, key_id="unknown"),
    ]

    for candidate in tampered:
        _assert_safe_failure(cipher, candidate, AAD)

    wrong_cipher = EnvelopeCipher({"old": WRONG_KEY}, current_key_id="old")
    _assert_safe_failure(wrong_cipher, envelope, AAD)


@pytest.mark.parametrize("bad_aad", [b"", b"wrong-aad", _runtime("not-bytes")])
def test_rewrap_requires_the_original_nonempty_byte_aad(bad_aad: Any) -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY, "new": NEW_KEY}, current_key_id="old")
    envelope = cipher.encrypt(PLAINTEXT, aad=AAD)

    with pytest.raises(ValueError):
        cipher.rewrap(envelope, aad=bad_aad, new_key_id="new")


def test_rewrap_changes_only_the_wrapped_dek_nonce_and_key_id() -> None:
    rotating = EnvelopeCipher({"old": OLD_KEY, "new": NEW_KEY}, current_key_id="old")
    original = rotating.encrypt(PLAINTEXT, aad=AAD)

    rewrapped = rotating.rewrap(original, aad=AAD, new_key_id="new")

    assert rewrapped.ciphertext == original.ciphertext
    assert rewrapped.nonce == original.nonce
    assert rewrapped.wrapped_dek != original.wrapped_dek
    assert rewrapped.wrap_nonce != original.wrap_nonce
    assert rewrapped.key_id == "new"
    assert (
        EnvelopeCipher({"new": NEW_KEY}, current_key_id="new").decrypt(rewrapped, aad=AAD)
        == PLAINTEXT
    )
    _assert_safe_failure(EnvelopeCipher({"old": OLD_KEY}, current_key_id="old"), rewrapped, AAD)
    assert (
        EnvelopeCipher({"old": OLD_KEY}, current_key_id="old").decrypt(original, aad=AAD)
        == PLAINTEXT
    )


def test_rewrap_rejects_unknown_target_key_without_exposing_plaintext() -> None:
    cipher = EnvelopeCipher({"old": OLD_KEY}, current_key_id="old")
    envelope = cipher.encrypt(PLAINTEXT, aad=AAD)

    with pytest.raises(ValueError) as caught:
        cipher.rewrap(envelope, aad=AAD, new_key_id="unknown")
    assert PLAINTEXT.decode() not in repr(caught.value)


def test_envelope_dataclass_has_no_plaintext_or_unwrapped_dek_field() -> None:
    assert {field.name for field in fields(EncryptedEnvelope)} == {
        "ciphertext",
        "nonce",
        "wrapped_dek",
        "wrap_nonce",
        "key_id",
    }
    assert not hasattr(EncryptedEnvelope(b"c", b"n", b"w", b"wn", "key"), "__dict__")
