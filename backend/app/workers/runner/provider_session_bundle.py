"""Encrypted, provider-scoped migration bundles for file-backed sessions."""

from __future__ import annotations

import base64
import json
import os
import stat
from pathlib import Path
from typing import Final, cast

from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import atomic_write_bytes, no_follow_flag
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.provider_cookie_lease import MAX_COOKIE_BYTES
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

_FORMAT: Final = "framefetch-provider-session-v1"
_MAGIC: Final = b"framefetch-provider-session-v1\x00"
_KEY_BYTES: Final = 32
_NONCE_BYTES: Final = 12
_MAX_BUNDLE_BYTES: Final = 2 * 1024 * 1024


def create_backup_key(path: Path) -> None:
    """Create a separate 0600 migration key without replacing an existing key."""
    path = path.absolute()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | no_follow_flag(),
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, os.urandom(_KEY_BYTES))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def encrypt_session_bundle(
    provider: ProviderKey,
    payload: bytes,
    *,
    key_file: Path,
    destination: Path,
) -> None:
    """Encrypt one validated provider payload for transfer to another host."""
    if not 0 < len(payload) <= MAX_COOKIE_BYTES:
        raise RunnerFailure("credential_rejected", status=422)
    key = _read_key(key_file)
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = ChaCha20Poly1305(key).encrypt(
        nonce,
        payload,
        _associated_data(provider),
    )
    document = {
        "format": _FORMAT,
        "provider": str(provider),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    destination = destination.absolute()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write_bytes(
        destination,
        (json.dumps(document, separators=(",", ":")) + "\n").encode("ascii"),
    )


def decrypt_session_bundle(
    provider: ProviderKey,
    *,
    key_file: Path,
    source: Path,
) -> bytes:
    """Decrypt one migration bundle in memory and bind it to its provider."""
    document = _read_bundle(source)
    if (
        document.get("format") != _FORMAT
        or document.get("provider") != str(provider)
        or not isinstance(document.get("nonce"), str)
        or not isinstance(document.get("ciphertext"), str)
    ):
        raise RunnerFailure("credential_rejected", status=422)
    nonce_text = cast(str, document["nonce"])
    ciphertext_text = cast(str, document["ciphertext"])
    try:
        nonce = base64.b64decode(nonce_text, validate=True)
        ciphertext = base64.b64decode(ciphertext_text, validate=True)
        if len(nonce) != _NONCE_BYTES:
            raise ValueError
        payload = ChaCha20Poly1305(_read_key(key_file)).decrypt(
            nonce,
            ciphertext,
            _associated_data(provider),
        )
    except (InvalidTag, ValueError, TypeError) as exc:
        raise RunnerFailure("credential_rejected", status=422) from exc
    if not 0 < len(payload) <= MAX_COOKIE_BYTES:
        raise RunnerFailure("credential_rejected", status=422)
    return payload


def _associated_data(provider: ProviderKey) -> bytes:
    return _MAGIC + str(provider).encode("ascii")


def _read_key(path: Path) -> bytes:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
        )
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
                or info.st_mode & 0o077
                or info.st_size != _KEY_BYTES
            ):
                raise OSError("unsafe provider-session backup key")
            return source.read(_KEY_BYTES + 1)
    except FileNotFoundError as exc:
        raise OSError("provider-session backup key is missing") from exc


def _read_bundle(path: Path) -> dict[str, object]:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
        )
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or not 0 < info.st_size <= _MAX_BUNDLE_BYTES
            ):
                raise OSError("unsafe provider-session bundle")
            payload = source.read(_MAX_BUNDLE_BYTES + 1)
    except FileNotFoundError as exc:
        raise OSError("provider-session bundle is missing") from exc
    try:
        document = json.loads(payload.decode("ascii"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise RunnerFailure("credential_rejected", status=422) from exc
    if not isinstance(document, dict):
        raise RunnerFailure("credential_rejected", status=422)
    return cast(dict[str, object], document)
