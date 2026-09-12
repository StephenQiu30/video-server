from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.api.errors import application_error
from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app
from app.services.downloads import ApplicationError, ApplicationErrorCode
from fastapi.testclient import TestClient


def test_provider_cooldown_exposes_only_bounded_retry_header():
    mapped = application_error(
        ApplicationError(
            ApplicationErrorCode.PROVIDER_RATE_LIMITED,
            retry_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )
    assert mapped.status == 429
    assert mapped.headers is not None
    assert 299 <= int(mapped.headers["Retry-After"]) <= 300
    assert "egress" not in mapped.detail


def test_app_error_uses_stable_problem_details(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test"))

    @app.get("/api/test-error")
    async def test_error() -> None:
        raise AppError(
            status=409,
            code="job_conflict",
            title="Job conflict",
            detail="The job cannot transition from its current state.",
        )

    with TestClient(app) as client:
        response = client.get("/api/test-error")

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "urn:video-server:error:job_conflict",
        "title": "Job conflict",
        "status": 409,
        "detail": "The job cannot transition from its current state.",
        "code": "job_conflict",
        "instance": "/api/test-error",
    }


def test_request_validation_uses_stable_problem_details(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test"))

    @app.get("/api/validation")
    async def validation(limit: int) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(app) as client:
        response = client.get("/api/validation", params={"limit": "invalid"})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "urn:video-server:error:invalid_request",
        "title": "Invalid request",
        "status": 422,
        "detail": "The request parameters are invalid.",
        "code": "invalid_request",
        "instance": "/api/validation",
    }
