from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum
import logging
from time import monotonic

from app.core.errors import AppError

logger = logging.getLogger(__name__)


class RateLimitScope(StrEnum):
    PARSE = "parse"
    CREATE_TASK = "create_task"
    LOGIN = "login"
    REGISTER = "register"


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: RateLimitScope
    limit: int
    window_seconds: int
    lock_seconds: int | None = None


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int | None = None


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int, scope: RateLimitScope = RateLimitScope.PARSE) -> None:
        self.policy = RateLimitPolicy(scope=scope, limit=limit, window_seconds=window_seconds)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def assert_allowed(self, identity: str) -> RateLimitResult:
        if self.policy.limit <= 0:
            return RateLimitResult(allowed=True, remaining=0)
        now = monotonic()
        key = _rate_limit_key(self.policy.scope, identity)
        hits = self._hits[key]
        while hits and now - hits[0] >= self.policy.window_seconds:
            hits.popleft()
        if len(hits) >= self.policy.limit:
            raise AppError("rate_limited", "请求过于频繁，请稍后再试", 429)
        hits.append(now)
        return RateLimitResult(allowed=True, remaining=max(0, self.policy.limit - len(hits)))


class RedisRateLimiter:
    def __init__(self, redis_client, policy: RateLimitPolicy, fail_open: bool = True) -> None:
        self.redis = redis_client
        self.policy = policy
        self.fail_open = fail_open

    def assert_allowed(self, identity: str) -> RateLimitResult:
        if self.policy.limit <= 0:
            return RateLimitResult(allowed=True, remaining=0)
        key = _rate_limit_key(self.policy.scope, identity)
        try:
            count = self.redis.incr(key)
            if count == 1:
                self.redis.expire(key, self.policy.window_seconds)
            if count > self.policy.limit:
                retry_after = self.redis.ttl(key)
                raise AppError("rate_limited", "请求过于频繁，请稍后再试", 429, {"retry_after_seconds": retry_after})
            return RateLimitResult(
                allowed=True,
                remaining=max(0, self.policy.limit - count),
                retry_after_seconds=self.redis.ttl(key),
            )
        except AppError:
            raise
        except Exception as exc:
            if not self.fail_open:
                raise AppError("rate_limited", "请求过于频繁，请稍后再试", 429) from exc
            logger.warning("Redis rate limiter unavailable; failing open: %s", exc)
            return RateLimitResult(allowed=True, remaining=0)


def _rate_limit_key(scope: RateLimitScope, identity: str) -> str:
    return f"video:ratelimit:{scope.value}:{identity}"
