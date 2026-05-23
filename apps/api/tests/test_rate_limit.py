from app.core.errors import AppError
from app.services.rate_limit import InMemoryRateLimiter


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
