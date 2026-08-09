"""Argon2 password hashing adapter."""

from __future__ import annotations

import asyncio
import secrets

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.application.auth import PasswordCheck


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash = self._password_hash.hash(secrets.token_urlsafe(32))

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._password_hash.hash, password)

    async def verify(self, password: str, password_hash: str | None) -> PasswordCheck:
        compared_hash = password_hash or self._dummy_hash
        try:
            valid, updated_hash = await asyncio.to_thread(
                self._password_hash.verify_and_update,
                password,
                compared_hash,
            )
        except UnknownHashError:
            return PasswordCheck(False)
        return PasswordCheck(valid and password_hash is not None, updated_hash)
