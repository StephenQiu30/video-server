from app.core.errors import AppError
from app.services.rate_limit import InMemoryRateLimiter, RateLimitPolicy, RateLimitScope, RedisRateLimiter


def test_in_memory_rate_limiter_rejects_after_limit() -> None:
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    limiter.assert_allowed("user:1")
    limiter.assert_allowed("user:1")

    try:
        limiter.assert_allowed("user:1")
    except AppError as exc:
        assert exc.code == "rate_limited"
        assert exc.status_code == 429
    else:
        raise AssertionError("expected rate limit")


def test_in_memory_rate_limiter_isolated_by_key() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    limiter.assert_allowed("user:1")

    limiter.assert_allowed("user:2")


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expires: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expires[key] = seconds

    def ttl(self, key: str) -> int:
        return self.expires.get(key, -1)


class BrokenRedis(FakeRedis):
    def incr(self, key: str) -> int:
        raise RuntimeError("redis down")


def test_redis_rate_limiter_uses_scope_key_and_ttl() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(
        redis_client=redis,
        policy=RateLimitPolicy(scope=RateLimitScope.PARSE, limit=1, window_seconds=60),
    )

    result = limiter.assert_allowed("user:7")

    assert result.allowed is True
    assert result.remaining == 0
    assert redis.values["video:ratelimit:parse:user:7"] == 1
    assert redis.expires["video:ratelimit:parse:user:7"] == 60

    try:
        limiter.assert_allowed("user:7")
    except AppError as exc:
        assert exc.code == "rate_limited"
        assert exc.status_code == 429
    else:
        raise AssertionError("expected redis-backed limiter to reject")


def test_redis_rate_limiter_fail_open_when_unavailable() -> None:
    limiter = RedisRateLimiter(
        redis_client=BrokenRedis(),
        policy=RateLimitPolicy(scope=RateLimitScope.CREATE_TASK, limit=1, window_seconds=60),
        fail_open=True,
    )

    result = limiter.assert_allowed("user:7")

    assert result.allowed is True
    assert result.remaining == 0
