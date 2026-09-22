"""User-owned authorization transactions backed by the local Access Agent queue."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from uuid import UUID

from redis.asyncio import Redis

from app.services.provider_types import ProviderAuthorizationSource, ProviderKey

_KEY_PREFIX = "video:provider-authorization:"
_ACTIVE_KEY_PREFIX = "video:provider-authorization-active:"
_TOKEN_BYTES = 16
_MAX_REQUEST_BYTES = 256
_DEFAULT_RESULT_RETENTION = timedelta(hours=24)

_CLAIM_TRANSACTION_SCRIPT = """
local existing = redis.call('GET', KEYS[1])
if existing then
  return existing
end
redis.call('SET', KEYS[1], ARGV[1], 'EX', tonumber(ARGV[2]))
redis.call(
  'HSET', KEYS[2],
  'user_id', ARGV[3],
  'provider_key', ARGV[4],
  'status', ARGV[5],
  'expires_at', ARGV[6],
  'active_key', KEYS[1]
)
redis.call('EXPIRE', KEYS[2], tonumber(ARGV[7]))
return ARGV[1]
"""

_TRANSITION_STATUS_SCRIPT = """
local current = redis.call('HGET', KEYS[1], 'status')
if current ~= ARGV[1] then
  return 0
end
redis.call('HSET', KEYS[1], 'status', ARGV[2])
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
return 1
"""

_RELEASE_ACTIVE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


class ProviderAuthorizationStatus:
    PENDING = "pending"
    SOURCE_AVAILABLE = "source_available"
    AUTHORIZATION_REQUIRED = "authorization_required"
    PERMISSION_REQUIRED = "permission_required"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProviderAuthorizationTransaction:
    transaction_id: str
    provider_key: str
    status: str
    expires_at: datetime


class ProviderAuthorizationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class ProviderAuthorizationRequest:
    """Non-secret authorization intent handed to the local queue adapter."""

    provider: ProviderKey
    expires_at: datetime
    source: ProviderAuthorizationSource = ProviderAuthorizationSource.DEDICATED_CHROME
    probe: bool = False

    def serialize(self) -> bytes:
        return json.dumps(
            {
                "provider": self.provider.value,
                "expires_at": self.expires_at.astimezone(UTC).isoformat(),
                "source": self.source.value,
                "probe": self.probe,
            },
            separators=(",", ":"),
        ).encode("ascii")

    @classmethod
    def parse(cls, payload: bytes) -> ProviderAuthorizationRequest:
        if not 0 < len(payload) <= _MAX_REQUEST_BYTES:
            raise ValueError("authorization request is outside the size limit")
        try:
            value = json.loads(payload.decode("ascii"))
            provider = ProviderKey(value["provider"])
            expires_at = datetime.fromisoformat(value["expires_at"])
            source = ProviderAuthorizationSource(
                value.get("source", ProviderAuthorizationSource.DEDICATED_CHROME.value)
            )
            probe = value.get("probe", False)
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid authorization request") from exc
        if expires_at.tzinfo is None or not isinstance(probe, bool):
            raise ValueError("authorization expiry must include a timezone")
        return cls(provider, expires_at.astimezone(UTC), source, probe)


class ProviderAuthorizationQueue(Protocol):
    """Filesystem or test adapter used by the authorization service."""

    def agent_ready(self, provider: ProviderKey) -> bool: ...

    def write_request(
        self, token: str, request: ProviderAuthorizationRequest
    ) -> None: ...

    def read_response(self, token: str) -> str | None: ...

    def remove_response(self, token: str) -> None: ...

    def cancel(self, token: str) -> None: ...


class ProviderAuthorizationService:
    """Persist only transaction metadata; Cookies stay inside the host agent."""

    def __init__(
        self,
        authorization_queue: ProviderAuthorizationQueue,
        redis_url: str,
        *,
        now: Callable[[], datetime],
        can_authorize_provider: Callable[[str], bool],
        transaction_ttl: timedelta = timedelta(minutes=10),
        result_retention: timedelta = _DEFAULT_RESULT_RETENTION,
    ) -> None:
        if transaction_ttl.total_seconds() <= 0:
            raise ValueError("provider authorization transaction TTL must be positive")
        if result_retention.total_seconds() <= 0:
            raise ValueError("provider authorization result retention must be positive")
        self._authorization_queue = authorization_queue
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._now = now
        self._can_authorize_provider = can_authorize_provider
        self._ttl = transaction_ttl
        self._result_retention = result_retention

    async def begin(
        self,
        user_id: UUID,
        provider_key: str,
        source: ProviderAuthorizationSource = (
            ProviderAuthorizationSource.CURRENT_CHROME
        ),
    ) -> ProviderAuthorizationTransaction:
        self._validate_provider(provider_key)
        try:
            authorization_source = ProviderAuthorizationSource(source)
        except ValueError as exc:
            raise ProviderAuthorizationError(
                "provider_unsupported", "该平台没有可用的本机授权流程。"
            ) from exc
        provider = ProviderKey(provider_key)
        active_key = self._active_key(user_id, provider, authorization_source)
        existing = await self._existing_active(user_id, active_key)
        if existing is not None:
            return existing
        if not await asyncio.to_thread(self._authorization_queue.agent_ready, provider):
            raise ProviderAuthorizationError(
                "provider_configuration_missing",
                "本机授权 Agent 尚未安装，请先完成一次本机初始化。",
            )
        token = secrets.token_hex(_TOKEN_BYTES)
        expires_at = self._now() + self._ttl
        key = self._key(token)
        operation_ttl = max(1, int(self._ttl.total_seconds()))
        ttl = max(1, int((self._ttl + self._result_retention).total_seconds()))
        claimed = False
        for _attempt in range(3):
            claimed_token = await self._redis.eval(
                _CLAIM_TRANSACTION_SCRIPT,
                2,
                active_key,
                key,
                token,
                operation_ttl,
                str(user_id),
                provider_key,
                ProviderAuthorizationStatus.PENDING,
                expires_at.astimezone(UTC).isoformat(),
                ttl,
            )
            if claimed_token == token:
                claimed = True
                break
            existing = await self._existing_active(user_id, active_key)
            if existing is not None:
                return existing
        if not claimed:
            raise ProviderAuthorizationError(
                "provider_authorization_unavailable",
                "同一平台的授权事务正在收敛，请稍后重试。",
            )
        try:
            self._authorization_queue.write_request(
                token,
                ProviderAuthorizationRequest(
                    provider,
                    expires_at,
                    authorization_source,
                ),
            )
        except Exception:
            await self._redis.delete(key)
            await self._release_active(active_key, token)
            raise ProviderAuthorizationError(
                "provider_authorization_unavailable",
                "本机授权队列暂时不可用，请检查本机 Agent 状态。",
            ) from None
        return ProviderAuthorizationTransaction(
            transaction_id=token,
            provider_key=provider_key,
            status=ProviderAuthorizationStatus.PENDING,
            expires_at=expires_at,
        )

    async def get(
        self,
        user_id: UUID,
        transaction_id: str,
    ) -> ProviderAuthorizationTransaction:
        record = await self._record_for_user(user_id, transaction_id)
        status = record["status"]
        expires_at = _parse_expiry(record["expires_at"])
        if status == ProviderAuthorizationStatus.PENDING:
            if self._now() >= expires_at:
                transitioned = await self._transition_status(
                    transaction_id,
                    ProviderAuthorizationStatus.PENDING,
                    ProviderAuthorizationStatus.EXPIRED,
                )
                if transitioned:
                    status = ProviderAuthorizationStatus.EXPIRED
                    _cancel_quietly(self._authorization_queue, transaction_id)
                    _remove_response_quietly(self._authorization_queue, transaction_id)
                else:
                    record = await self._record_for_user(user_id, transaction_id)
                    status = record["status"]
            elif (
                response := self._authorization_queue.read_response(transaction_id)
            ) is not None:
                response_status = _response_status(response)
                transitioned = await self._transition_status(
                    transaction_id,
                    ProviderAuthorizationStatus.PENDING,
                    response_status,
                )
                if transitioned:
                    status = response_status
                    self._authorization_queue.remove_response(transaction_id)
                else:
                    record = await self._record_for_user(user_id, transaction_id)
                    status = record["status"]
                    if status != ProviderAuthorizationStatus.PENDING:
                        _remove_response_quietly(
                            self._authorization_queue, transaction_id
                        )
        else:
            _remove_response_quietly(self._authorization_queue, transaction_id)
        return ProviderAuthorizationTransaction(
            transaction_id=transaction_id,
            provider_key=record["provider_key"],
            status=status,
            expires_at=expires_at,
        )

    async def cancel(self, user_id: UUID, transaction_id: str) -> None:
        record = await self._record_for_user(user_id, transaction_id)
        if record["status"] == ProviderAuthorizationStatus.PENDING:
            transitioned = await self._transition_status(
                transaction_id,
                ProviderAuthorizationStatus.PENDING,
                ProviderAuthorizationStatus.CANCELLED,
            )
            if transitioned:
                _cancel_quietly(self._authorization_queue, transaction_id)
                _remove_response_quietly(self._authorization_queue, transaction_id)

    async def close(self) -> None:
        await self._redis.aclose()

    def _validate_provider(self, provider_key: str) -> None:
        try:
            ProviderKey(provider_key)
        except ValueError as exc:
            raise ProviderAuthorizationError(
                "provider_unsupported", "该平台没有可用的本机授权流程。"
            ) from exc
        if not self._can_authorize_provider(provider_key):
            raise ProviderAuthorizationError(
                "provider_unsupported", "该平台没有可用的本机授权流程。"
            )

    async def _record_for_user(
        self,
        user_id: UUID,
        transaction_id: str,
    ) -> dict[str, str]:
        if len(transaction_id) != _TOKEN_BYTES * 2 or any(
            character not in "0123456789abcdef" for character in transaction_id
        ):
            raise ProviderAuthorizationError("not_found", "授权事务不存在或已经过期。")
        record = cast(
            dict[str, str], await self._redis.hgetall(self._key(transaction_id))
        )
        stored_user_id = record.get("user_id")
        if (
            not record
            or stored_user_id is None
            or not hmac.compare_digest(stored_user_id, str(user_id))
        ):
            raise ProviderAuthorizationError("not_found", "授权事务不存在或已经过期。")
        return record

    async def _transition_status(
        self,
        transaction_id: str,
        expected: str,
        target: str,
    ) -> bool:
        retention = max(1, int(self._result_retention.total_seconds()))
        record = cast(
            dict[str, str], await self._redis.hgetall(self._key(transaction_id))
        )
        changed = await self._redis.eval(
            _TRANSITION_STATUS_SCRIPT,
            1,
            self._key(transaction_id),
            expected,
            target,
            retention,
        )
        if changed and (active_key := record.get("active_key")):
            await self._release_active(active_key, transaction_id)
        return bool(changed)

    async def _existing_active(
        self,
        user_id: UUID,
        active_key: str,
    ) -> ProviderAuthorizationTransaction | None:
        value = await self._redis.get(active_key)
        if not isinstance(value, str):
            return None
        try:
            record = await self._record_for_user(user_id, value)
        except ProviderAuthorizationError:
            await self._release_active(active_key, value)
            return None
        if record.get("status") != ProviderAuthorizationStatus.PENDING:
            await self._release_active(active_key, value)
            return None
        expires_at = _parse_expiry(record["expires_at"])
        if self._now() >= expires_at:
            await self._transition_status(
                value,
                ProviderAuthorizationStatus.PENDING,
                ProviderAuthorizationStatus.EXPIRED,
            )
            return None
        return ProviderAuthorizationTransaction(
            transaction_id=value,
            provider_key=record["provider_key"],
            status=record["status"],
            expires_at=expires_at,
        )

    async def _release_active(self, active_key: str, transaction_id: str) -> None:
        await self._redis.eval(
            _RELEASE_ACTIVE_SCRIPT,
            1,
            active_key,
            transaction_id,
        )

    @staticmethod
    def _key(transaction_id: str) -> str:
        digest = hashlib.sha256(transaction_id.encode("ascii")).hexdigest()
        return _KEY_PREFIX + digest

    @staticmethod
    def _active_key(
        user_id: UUID,
        provider: ProviderKey,
        source: ProviderAuthorizationSource,
    ) -> str:
        identity = f"{user_id}:{provider.value}:{source.value}"
        return _ACTIVE_KEY_PREFIX + hashlib.sha256(identity.encode()).hexdigest()


def _parse_expiry(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("authorization expiry must include a timezone")
    return parsed.astimezone(UTC)


def _response_status(value: str) -> str:
    if value in {"authorized", "source_available"}:
        return ProviderAuthorizationStatus.SOURCE_AVAILABLE
    if value == "cancelled":
        return ProviderAuthorizationStatus.CANCELLED
    if value == "expired":
        return ProviderAuthorizationStatus.EXPIRED
    if value == "credential_required":
        return ProviderAuthorizationStatus.AUTHORIZATION_REQUIRED
    if value == "provider_session_permission_denied":
        return ProviderAuthorizationStatus.PERMISSION_REQUIRED
    return ProviderAuthorizationStatus.FAILED


def _cancel_quietly(
    authorization_queue: ProviderAuthorizationQueue, transaction_id: str
) -> None:
    try:
        authorization_queue.cancel(transaction_id)
    except OSError:
        pass


def _remove_response_quietly(
    authorization_queue: ProviderAuthorizationQueue, transaction_id: str
) -> None:
    try:
        authorization_queue.remove_response(transaction_id)
    except OSError:
        pass
