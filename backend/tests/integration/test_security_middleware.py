from pathlib import Path

from app.core.config import Settings
from app.infrastructure.rate_limiter import RateLimitExceeded
from app.main import create_app
from fastapi.testclient import TestClient


def test_request_guard_rejects_large_bodies_and_adds_security_headers(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            app_env="test",
            frontend_dist_dir=tmp_path / "missing",
            request_max_bytes=1024,
        )
    )

    with TestClient(app) as client:
        response = client.post("/health/live", content=b"x" * 1025)

    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_rate_limit_returns_problem_details_and_retry_after(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "missing"))

    class BlockedLimiter:
        async def check(self, **_kwargs: object) -> None:
            raise RateLimitExceeded(7)

    app.state.rate_limiter = BlockedLimiter()
    with TestClient(app) as client:
        response = client.post(
            "/api/inspections",
            headers={"Idempotency-Key": "inspect-1"},
            json={"url": "https://media.example/video"},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"
    assert response.json()["code"] == "rate_limited"
