from unittest.mock import AsyncMock

import pytest
from app.config import Settings
from app.integrations.rate_limiter import RedisRateLimiter
from app.rate_limits import RateLimitPolicy
from pydantic import ValidationError


def test_rate_limits_can_be_overridden_without_losing_other_defaults(monkeypatch):
    monkeypatch.setenv(
        "RATE_LIMIT_POLICIES", '{"analysis":{"limit":2,"window_seconds":90}}'
    )
    settings = Settings(app_env="test", _env_file=None)
    limiter = RedisRateLimiter(
        "redis://localhost:6379", b"a" * 32, policies=settings.rate_limit_policies
    )
    assert limiter._policies["analysis"] == RateLimitPolicy(limit=2, window_seconds=90)
    assert limiter._policies["analysis_retry"].limit == 5


@pytest.mark.parametrize(
    "policy",
    [
        {"analysis": {"limit": 0, "window_seconds": 60}},
        {"analyis": {"limit": 2, "window_seconds": 60}},
        {"analysis": {"limit": 2, "window_seconds": 0}},
    ],
)
def test_invalid_rate_policy_fails_configuration(policy):
    with pytest.raises(ValidationError):
        Settings(app_env="test", _env_file=None, rate_limit_policies=policy)


async def test_authenticated_limits_use_only_the_user_dimension() -> None:
    limiter = RedisRateLimiter("redis://localhost:6379", b"a" * 32)
    limiter._client.eval = AsyncMock(return_value=[0, 60])

    await limiter.check(operation="download", owner_hash="b" * 64)
    assert limiter._client.eval.await_args.args[1] == 1

    await limiter.check(
        operation="login", owner_hash="c" * 64, client_host="203.0.113.10"
    )
    assert limiter._client.eval.await_args.args[1] == 2
