"""Encrypted, provider-scoped snapshots received from the browser connector.

The browser connector is the only component allowed to read the user's current
Chrome session.  The background Access Agent never opens Chrome's SQLite
database; it only reads these short-lived, allowlisted snapshots.
"""

from __future__ import annotations

import fcntl
import os
import stat
from pathlib import Path

from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import (
    atomic_write_bytes,
    ensure_private_directory,
    no_follow_flag,
    validate_private_file,
)
from app.workers.runner.netscape_cookie import live_cookie_payload
from app.workers.runner.provider_cookie_lease import MAX_COOKIE_BYTES
from app.workers.runner.provider_session_policy import (
    ProviderSessionSource,
    browser_session_policy,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

_KEY_BYTES = 32
_NONCE_BYTES = 12
_HEADER = b"framefetch-browser-bridge-v1\n"
_MAX_SNAPSHOT_BYTES = MAX_COOKIE_BYTES + len(_HEADER) + _NONCE_BYTES + 16


class ProviderBrowserBridgeStore:
    """Store only encrypted, provider-scoped browser snapshots on the host."""

    def __init__(self, runtime_root: Path) -> None:
        if not runtime_root.is_absolute():
            raise ValueError("browser bridge runtime root must be absolute")
        self._root = runtime_root / "bridge"
        ensure_private_directory(self._root)

    def prepare(self) -> None:
        """Create the local key once; no Cookie material is written here."""
        self._key()

    def write(self, provider: ProviderKey, payload: bytes) -> None:
        policy = browser_session_policy(provider)
        if policy.source is not ProviderSessionSource.CHROME_PROFILE:
            raise ValueError("provider does not support browser bridge sessions")
        live, names = live_cookie_payload(payload, frozenset(policy.domains))
        if not policy.accepts(names):
            raise ValueError("browser snapshot does not contain a usable session")
        nonce = os.urandom(_NONCE_BYTES)
        ciphertext = ChaCha20Poly1305(self._key()).encrypt(
            nonce,
            live,
            provider.value.encode("ascii"),
        )
        atomic_write_bytes(
            self._path(provider),
            _HEADER + nonce + ciphertext,
            mode=0o600,
        )

    def remove(self, provider: ProviderKey) -> None:
        path = self._path(provider)
        try:
            info = path.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise OSError("unsafe browser bridge snapshot")
        path.unlink()

    def clear(self) -> None:
        """Remove all encrypted browser material during explicit uninstall."""

        for path in self._root.iterdir():
            if path.name not in {".key", ".key.lock"} and not path.name.endswith(
                ".snapshot"
            ):
                continue
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise OSError("unsafe browser bridge entry")
            path.unlink()
        self._root.rmdir()

    def read(self, provider: ProviderKey) -> bytes | None:
        policy = browser_session_policy(provider)
        if policy.source is not ProviderSessionSource.CHROME_PROFILE:
            return None
        path = self._path(provider)
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
            )
        except FileNotFoundError:
            return None
        with os.fdopen(descriptor, "rb", closefd=True) as source:
            validate_private_file(source.fileno(), "unsafe browser bridge snapshot")
            info = os.fstat(source.fileno())
            if info.st_size <= len(_HEADER) + _NONCE_BYTES + 16:
                return None
            if info.st_size > _MAX_SNAPSHOT_BYTES:
                return None
            encrypted = source.read(_MAX_SNAPSHOT_BYTES + 1)
        if len(encrypted) > _MAX_SNAPSHOT_BYTES or not encrypted.startswith(_HEADER):
            return None
        nonce_start = len(_HEADER)
        nonce = encrypted[nonce_start : nonce_start + _NONCE_BYTES]
        ciphertext = encrypted[nonce_start + _NONCE_BYTES :]
        try:
            payload = ChaCha20Poly1305(self._key()).decrypt(
                nonce,
                ciphertext,
                provider.value.encode("ascii"),
            )
            live, names = live_cookie_payload(payload, frozenset(policy.domains))
        except Exception:
            return None
        return live if policy.accepts(names) else None

    def _path(self, provider: ProviderKey) -> Path:
        return self._root / f"{provider.value}.snapshot"

    def _key(self) -> bytes:
        try:
            return self._read_key()
        except FileNotFoundError:
            pass
        # Native hosts run in separate processes. Serialize first publication,
        # then atomically expose a complete key; O_EXCL alone exposes 0 bytes.
        lock = os.open(
            self._root / ".key.lock",
            os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | no_follow_flag(),
            0o600,
        )
        try:
            validate_private_file(lock, "unsafe browser bridge key lock")
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return self._read_key()
            except FileNotFoundError:
                atomic_write_bytes(self._root / ".key", os.urandom(_KEY_BYTES))
                return self._read_key()
        finally:
            os.close(lock)

    def _read_key(self) -> bytes:
        descriptor = os.open(
            self._root / ".key",
            os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
        )
        with os.fdopen(descriptor, "rb", closefd=True) as source:
            validate_private_file(source.fileno(), "unsafe browser bridge key")
            payload = source.read(_KEY_BYTES + 1)
        if len(payload) != _KEY_BYTES:
            raise OSError("invalid browser bridge key")
        return payload
