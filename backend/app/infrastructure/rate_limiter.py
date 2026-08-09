"""Atomic Valkey fixed-window limiter for expensive public operations."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis


class RateLimiterUnavailable(RuntimeError):
    """The shared limiter cannot make a safe admission decision."""


@dataclass(frozen=True, slots=True)
class RateLimitExceeded(Exception):
    retry_after: int


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.limit < 1 or self.window_seconds < 1:
            raise ValueError("rate limit policy must be positive")


_INCREMENT_SCRIPT = """
local denied = 0
local retry = 0
for _, key in ipairs(KEYS) do
  local count = redis.call('INCR', key)
  if count == 1 then redis.call('EXPIRE', key, ARGV[1]) end
  local ttl = redis.call('TTL', key)
  if ttl > retry then retry = ttl end
  if count > tonumber(ARGV[2]) then denied = 1 end
end
if denied == 1 then
  for _, key in ipairs(KEYS) do redis.call('DECR', key) end
end
return {denied, retry}
"""


class ValkeyRateLimiter:
    def __init__(self, url: str, salt: bytes) -> None:
        if not url or len(salt) < 16:
            raise ValueError("rate limiter URL and salt are required")
        self._client: Any = Redis.from_url(url, decode_responses=False)
        self._salt = salt

    async def check(self, *, operation: str, owner_hash: str, client_host: str) -> None:
        policy = _POLICIES[operation]
        keys = [
            self._key(operation, "ip", client_host, policy.window_seconds),
            self._key(operation, "owner", owner_hash, policy.window_seconds),
        ]
        try:
            result = await self._client.eval(
                _INCREMENT_SCRIPT,
                len(keys),
                *keys,
                str(policy.window_seconds),
                str(policy.limit),
            )
        except Exception as exc:
            raise RateLimiterUnavailable from exc
        denied = int(result[0])
        if denied:
            raise RateLimitExceeded(max(1, int(result[1])))

    async def close(self) -> None:
        await self._client.aclose()

    async def ping(self) -> None:
        try:
            await self._client.ping()
        except Exception as exc:
            raise RateLimiterUnavailable from exc

    def _key(self, operation: str, dimension: str, value: str, window: int) -> str:
        digest = hmac.new(
            self._salt,
            f"{dimension}:{value}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"video:ratelimit:{operation}:{window}:{digest}"


_POLICIES = {
    "login": RateLimitPolicy(limit=10, window_seconds=60),
    "register": RateLimitPolicy(limit=5, window_seconds=3600),
    "inspect": RateLimitPolicy(limit=20, window_seconds=60),
    "download": RateLimitPolicy(limit=10, window_seconds=60),
    "analysis": RateLimitPolicy(limit=5, window_seconds=60),
}
