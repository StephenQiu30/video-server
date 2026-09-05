import pytest
from app.core.config import Settings
from app.core.rate_limits import RateLimitPolicy
from app.infrastructure.rate_limiter import ValkeyRateLimiter
from pydantic import ValidationError


def test_rate_limits_can_be_overridden_without_losing_other_defaults(monkeypatch):
    monkeypatch.setenv(
        "RATE_LIMIT_POLICIES", '{"analysis":{"limit":2,"window_seconds":90}}'
    )
    settings = Settings(app_env="test", _env_file=None)
    limiter = ValkeyRateLimiter(
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
