"""Redis-backed refresh sessions with a PostgreSQL account repository."""

from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis

from app.repositories.auth.auth_repository import SqlAlchemyAuthRepository
from app.services.auth.errors import SessionRotationConflict
from app.services.auth.models import AccountRecord, CurrentUser, UserRole

_SESSION_KEY_PREFIX = "video:auth:session:"
_USER_SESSIONS_KEY_PREFIX = "video:auth:user-sessions:"
_ROTATED_PREFIX = "rotated:"
_ROTATION_GRACE_SECONDS = 10

_ROTATE_SESSION_SCRIPT = """
local current_user = redis.call('GET', KEYS[1])
if current_user and string.sub(current_user, 1, 8) == 'rotated:' then
  return 2
end
if not current_user or current_user ~= ARGV[1] then
  return 0
end

redis.call('SET', KEYS[1], 'rotated:' .. ARGV[1], 'EX', ARGV[5])
redis.call('SREM', KEYS[3], ARGV[2])
redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[3])
redis.call('SADD', KEYS[3], ARGV[4])
redis.call('EXPIRE', KEYS[3], ARGV[3])
return 1
"""


class RedisAuthSessionStore:
    """Store only refresh-token hashes in Redis with an atomic rotation."""

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("auth session store URL is required")
        self._client = Redis.from_url(url, decode_responses=True)

    async def create_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        del session_id
        ttl = _ttl_seconds(expires_at, now)
        user_key = _user_sessions_key(user_id)
        pipeline = self._client.pipeline(transaction=True)
        pipeline.set(_session_key(token_hash), str(user_id), ex=ttl)
        pipeline.sadd(user_key, token_hash)
        pipeline.expire(user_key, ttl)
        await pipeline.execute()

    async def user_id_for_session(self, token_hash: str) -> UUID | None:
        value = await self._client.get(_session_key(token_hash))
        if not isinstance(value, str):
            return None
        if value.startswith(_ROTATED_PREFIX):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    async def is_rotated(self, token_hash: str) -> bool:
        value = await self._client.get(_session_key(token_hash))
        return isinstance(value, str) and value.startswith(_ROTATED_PREFIX)

    async def delete_session(self, token_hash: str) -> None:
        user_id = await self.user_id_for_session(token_hash)
        pipeline = self._client.pipeline(transaction=True)
        pipeline.delete(_session_key(token_hash))
        if user_id is not None:
            pipeline.srem(_user_sessions_key(user_id), token_hash)
        await pipeline.execute()

    async def replace_session(
        self,
        *,
        previous_token_hash: str,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> bool:
        del session_id
        ttl = _ttl_seconds(expires_at, now)
        result = await self._client.eval(
            _ROTATE_SESSION_SCRIPT,
            3,
            _session_key(previous_token_hash),
            _session_key(token_hash),
            _user_sessions_key(user_id),
            str(user_id),
            previous_token_hash,
            str(ttl),
            token_hash,
            str(_ROTATION_GRACE_SECONDS),
        )
        if int(result) == 2:
            raise SessionRotationConflict
        return int(result) == 1

    async def delete_user_sessions(self, user_id: UUID) -> None:
        user_key = _user_sessions_key(user_id)
        token_hashes = await self._client.smembers(user_key)
        pipeline = self._client.pipeline(transaction=True)
        for token_hash in token_hashes:
            if isinstance(token_hash, str):
                pipeline.delete(_session_key(token_hash))
        pipeline.delete(user_key)
        await pipeline.execute()

    async def ping(self) -> None:
        await self._client.ping()

    async def close(self) -> None:
        await self._client.aclose()


class RedisAuthRepository:
    """Use Redis for new sessions while reading legacy SQL sessions once."""

    def __init__(
        self,
        database: SqlAlchemyAuthRepository,
        sessions: RedisAuthSessionStore,
    ) -> None:
        self._database = database
        self._sessions = sessions

    async def create_account(
        self,
        *,
        account_id: UUID,
        username: str,
        normalized_username: str,
        email: str,
        password_hash: str,
        role: UserRole,
        now: datetime,
    ) -> AccountRecord:
        return await self._database.create_account(
            account_id=account_id,
            username=username,
            normalized_username=normalized_username,
            email=email,
            password_hash=password_hash,
            role=role,
            now=now,
        )

    async def has_accounts(self) -> bool:
        return await self._database.has_accounts()

    async def find_account_by_email(self, email: str) -> AccountRecord | None:
        return await self._database.find_account_by_email(email)

    async def find_account_by_id(self, account_id: UUID) -> AccountRecord | None:
        return await self._database.find_account_by_id(account_id)

    async def update_password_hash(
        self, account_id: UUID, password_hash: str, now: datetime
    ) -> None:
        await self._database.update_password_hash(account_id, password_hash, now)

    async def create_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        await self._sessions.create_session(
            session_id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            now=now,
        )

    async def find_user_by_session(
        self, token_hash: str, now: datetime
    ) -> CurrentUser | None:
        user_id = await self._sessions.user_id_for_session(token_hash)
        if user_id is not None:
            account = await self._database.find_account_by_id(user_id)
            if account is None or not account.is_active:
                return None
            return account.public_view()
        if await self._sessions.is_rotated(token_hash):
            raise SessionRotationConflict

        # Existing SQL sessions remain refreshable during the migration window.
        return await self._database.find_user_by_session(token_hash, now)

    async def delete_session(self, token_hash: str) -> None:
        await self._sessions.delete_session(token_hash)
        await self._database.delete_session(token_hash)

    async def replace_session(
        self,
        *,
        previous_token_hash: str,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> bool:
        replaced = await self._sessions.replace_session(
            previous_token_hash=previous_token_hash,
            session_id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            now=now,
        )
        if replaced:
            return True

        # A pre-migration SQL session is atomically rotated in SQL instead.
        return await self._database.replace_session(
            previous_token_hash=previous_token_hash,
            session_id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            now=now,
        )


def _session_key(token_hash: str) -> str:
    return f"{_SESSION_KEY_PREFIX}{token_hash}"


def _user_sessions_key(user_id: UUID) -> str:
    return f"{_USER_SESSIONS_KEY_PREFIX}{user_id}"


def _ttl_seconds(expires_at: datetime, now: datetime) -> int:
    return max(1, math.ceil((expires_at - now).total_seconds()))
