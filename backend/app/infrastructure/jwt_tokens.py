"""Signed access and refresh JWT adapter."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

from app.application.auth import IssuedTokens, TokenClaims


class JwtTokenService:
    def __init__(
        self,
        *,
        secret: bytes,
        issuer: str,
        audience: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("JWT secret must contain at least 32 bytes")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    def issue(self, user_id: UUID, now: datetime) -> IssuedTokens:
        access = self._encode(user_id, "access", now, self._access_ttl)
        refresh = self._encode(user_id, "refresh", now, self._refresh_ttl)
        return IssuedTokens(
            access_token=access,
            refresh_token=refresh,
            refresh_token_hash=self.digest(refresh),
            access_expires_at=now + self._access_ttl,
            refresh_expires_at=now + self._refresh_ttl,
        )

    def decode_access(self, token: str) -> TokenClaims | None:
        return self._decode(token, "access")

    def decode_refresh(self, token: str) -> TokenClaims | None:
        return self._decode(token, "refresh")

    def digest(self, token: str) -> str:
        if not token or len(token) > 4096:
            return ""
        return hmac.new(self._secret, token.encode(), hashlib.sha256).hexdigest()

    def _encode(
        self,
        user_id: UUID,
        token_type: Literal["access", "refresh"],
        now: datetime,
        ttl: timedelta,
    ) -> str:
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "jti": str(uuid4()),
            "type": token_type,
            "iat": now,
            "exp": now + ttl,
            "iss": self._issuer,
            "aud": self._audience,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def _decode(
        self, token: str, expected_type: Literal["access", "refresh"]
    ) -> TokenClaims | None:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["sub", "jti", "type", "iat", "exp", "iss", "aud"]},
            )
            if payload["type"] != expected_type:
                return None
            return TokenClaims(
                user_id=UUID(payload["sub"]),
                token_id=UUID(payload["jti"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except (InvalidTokenError, KeyError, TypeError, ValueError):
            return None
