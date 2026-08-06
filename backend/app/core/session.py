"""Signed anonymous sessions used to isolate user-owned resources."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime


class SessionError(ValueError):
    """A stable session validation error."""


@dataclass(frozen=True, slots=True)
class AnonymousSession:
    session_id: str
    issued_at: int
    token: str

    @property
    def owner_hash(self) -> str:
        return hashlib.sha256(self.session_id.encode()).hexdigest()


class SessionManager:
    def __init__(self, secret: bytes, *, ttl_seconds: int) -> None:
        if len(secret) < 32:
            raise ValueError("session secret must contain at least 32 bytes")
        self._secret = secret
        self._ttl_seconds = ttl_seconds

    def issue(self, *, now: datetime | None = None) -> AnonymousSession:
        current = now or datetime.now(UTC)
        session_id = secrets.token_urlsafe(24)
        issued_at = int(current.timestamp())
        payload = f"{session_id}:{issued_at}".encode()
        token = f"{_encode(payload)}.{_encode(self._sign(payload))}"
        return AnonymousSession(session_id, issued_at, token)

    def verify(self, token: str, *, now: datetime | None = None) -> AnonymousSession:
        try:
            encoded_payload, encoded_signature = token.split(".", maxsplit=1)
            payload = _decode(encoded_payload)
            signature = _decode(encoded_signature)
            session_id, issued_text = payload.decode().rsplit(":", maxsplit=1)
            issued_at = int(issued_text)
        except (ValueError, UnicodeDecodeError) as exc:
            raise SessionError("invalid_session") from exc
        if not hmac.compare_digest(signature, self._sign(payload)):
            raise SessionError("invalid_session")
        current = int((now or datetime.now(UTC)).timestamp())
        age = current - issued_at
        if age < -30 or age > self._ttl_seconds:
            raise SessionError("expired_session")
        return AnonymousSession(session_id, issued_at, token)

    def _sign(self, payload: bytes) -> bytes:
        return hmac.digest(self._secret, payload, "sha256")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode()


def _decode(value: str) -> bytes:
    return base64.b64decode(value, altchars=b"-_", validate=True)
